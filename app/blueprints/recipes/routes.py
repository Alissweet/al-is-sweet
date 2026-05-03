from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app import db
from app.models import Recipe, Ingredient, Step, Category, Tag, CookingHistory
from app.forms import RecipeForm
from app.utils.helpers import save_image, safe_int, safe_float, safe_str
import os
import random
import logging

recipes_bp = Blueprint('recipes', __name__)
logger = logging.getLogger(__name__)


# ── INDEX ────────────────────────────────────────────────────
@recipes_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    max_time = request.args.get('max_time', type=int)
    sort = request.args.get('sort', 'date_desc')
    tag = request.args.get('tag', '')

    query = Recipe.query.filter_by(user_id=current_user.id)

    if category == 'favorites':
        query = query.filter(Recipe.is_favorite == True)
    elif category:
        query = query.filter(Recipe.category == category)

    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f'%{search}%'),
                Recipe.tags.any(Tag.name.ilike(f'%{search}%'))
            )
        )

    if difficulty:
        query = query.filter(Recipe.difficulty == difficulty)

    if max_time:
        query = query.filter(
            (func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)) <= max_time
        )

    if tag:
        query = query.filter(Recipe.tags.any(Tag.name == tag))

    if sort == 'alpha_asc':
        query = query.order_by(Recipe.title.asc())
    elif sort == 'time_asc':
        query = query.order_by(
            (func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)).asc())
    elif sort == 'difficulty_asc':
        difficulty_order = case(
            {'Facile': 1, 'Moyen': 2, 'Difficile': 3},
            value=Recipe.difficulty, else_=4
        )
        query = query.order_by(difficulty_order.asc())
    elif sort == 'date_asc':
        query = query.order_by(Recipe.created_at.asc())
    else:
        query = query.order_by(Recipe.created_at.desc())

    recipes = query.paginate(page=page, per_page=9, error_out=False)
    categories = [c.name for c in Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()]
    available_tags = Tag.query.filter_by(user_id=current_user.id)\
        .join(Tag.recipes).filter(Recipe.user_id == current_user.id)\
        .distinct().order_by(Tag.name).all()

    return render_template('index.html',
                           recipes=recipes,
                           categories=categories,
                           current_category=category,
                           search=search,
                           current_difficulty=difficulty,
                           current_max_time=max_time,
                           current_sort=sort,
                           current_tag=tag,
                           available_tags=available_tags)


# ── DETAIL ───────────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>')
@login_required
def recipe_detail(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        flash("Vous n'avez pas accès à cette recette.", 'danger')
        return redirect(url_for('recipes.index'))

    similar_recipes = []
    if recipe.tags:
        tag_ids = [t.id for t in recipe.tags]
        similar_recipes = Recipe.query.filter(
            Recipe.user_id == current_user.id,
            Recipe.id != recipe.id,
            Recipe.tags.any(Tag.id.in_(tag_ids))
        ).order_by(Recipe.created_at.desc()).limit(3).all()

    return render_template('recipe_detail.html', recipe=recipe, similar_recipes=similar_recipes)


# ── CREATION ─────────────────────────────────────────────────
@recipes_bp.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def recipe_new():
    form = RecipeForm()
    if request.method == 'POST':
        try:
            servings = max(1, request.form.get('servings', 4, type=int) or 4)
            total_carbs = max(0, float(request.form.get('total_carbs', 0) or 0))

            recipe = Recipe(
                user_id=current_user.id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                tips=request.form.get('tips'),
                source=request.form.get('source', '').strip() or None,
                prep_time=request.form.get('prep_time', type=int),
                cook_time=request.form.get('cook_time', type=int),
                servings=servings,
                difficulty=request.form.get('difficulty'),
                category=request.form.get('category'),
                total_carbs=total_carbs
            )

            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    filename = save_image(file)
                    if filename:
                        recipe.image_filename = filename

            db.session.add(recipe)
            db.session.flush()

            _save_ingredients(recipe.id, request.form)
            _save_steps(recipe.id, request.form)
            _save_tags(recipe, request.form.get('tags', ''))

            db.session.commit()
            flash('Recette créée avec succès !', 'success')
            return redirect(url_for('recipes.recipe_detail', id=recipe.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur création recette: {e}")
            flash(f'Erreur lors de la création : {str(e)}', 'danger')

    categories = [c.name for c in Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()]
    return render_template('recipe_form.html', form=form, recipe=None, categories=categories)


# ── EDITION ──────────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def recipe_edit(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        flash('Vous ne pouvez pas modifier cette recette.', 'danger')
        return redirect(url_for('recipes.index'))

    form = RecipeForm(obj=recipe)
    categories = [c.name for c in Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()]

    if request.method == 'POST':
        try:
            recipe.title = request.form.get('title')
            recipe.description = request.form.get('description')
            recipe.tips = request.form.get('tips')
            recipe.source = request.form.get('source', '').strip() or None
            recipe.prep_time = max(0, request.form.get('prep_time', type=int) or 0)
            recipe.cook_time = max(0, request.form.get('cook_time', type=int) or 0)
            recipe.servings = max(1, request.form.get('servings', 4, type=int))
            recipe.difficulty = request.form.get('difficulty')
            recipe.category = request.form.get('category')
            try:
                recipe.total_carbs = max(0, float(request.form.get('total_carbs', 0)))
            except ValueError:
                recipe.total_carbs = 0.0

            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    if recipe.image_filename and not recipe.image_filename.startswith('http'):
                        old_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
                        if os.path.exists(old_path):
                            try:
                                os.remove(old_path)
                            except Exception as e:
                                logger.error(f"Erreur suppression image: {e}")
                    filename = save_image(file)
                    if filename:
                        recipe.image_filename = filename

            Ingredient.query.filter_by(recipe_id=recipe.id).delete()
            Step.query.filter_by(recipe_id=recipe.id).delete()
            _save_ingredients(recipe.id, request.form)
            _save_steps(recipe.id, request.form)
            _save_tags(recipe, request.form.get('tags', ''))

            db.session.commit()
            flash('Recette modifiée avec succès !', 'success')
            return redirect(url_for('recipes.recipe_detail', id=recipe.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur modification recette: {e}")
            flash(f'Erreur lors de la sauvegarde : {str(e)}', 'danger')

    return render_template('recipe_form.html', form=form, recipe=recipe, categories=categories)


# ── SUPPRESSION ──────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/delete', methods=['POST'])
@login_required
def recipe_delete(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        flash('Vous ne pouvez pas supprimer cette recette.', 'danger')
        return redirect(url_for('recipes.index'))

    if recipe.image_filename and not recipe.image_filename.startswith('http'):
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Erreur suppression image: {e}")

    db.session.delete(recipe)
    db.session.commit()
    flash('Recette supprimée.', 'success')
    return redirect(url_for('recipes.index'))


@recipes_bp.route('/recipes/delete-bulk', methods=['POST'])
@login_required
def recipes_delete_bulk():
    ids_raw = request.form.get('ids', '')
    if not ids_raw:
        flash('Aucune recette sélectionnée.', 'warning')
        return redirect(url_for('recipes.all_recipes'))

    ids = [int(i) for i in ids_raw.split(',') if i.strip().isdigit()]
    deleted = 0
    for recipe_id in ids:
        recipe = db.session.get(Recipe, recipe_id)
        if recipe and recipe.user_id == current_user.id:
            if recipe.image_filename and not recipe.image_filename.startswith('http'):
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.error(f"Erreur suppression image: {e}")
            db.session.delete(recipe)
            deleted += 1

    db.session.commit()
    flash(f'{deleted} recette(s) supprimée(s).', 'success')
    return redirect(url_for('recipes.all_recipes'))


# ── FAVORIS ──────────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée'}), 403

    recipe.is_favorite = not recipe.is_favorite
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'is_favorite': recipe.is_favorite,
            'message': 'Ajouté aux favoris' if recipe.is_favorite else 'Retiré des favoris'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


# ── NOTATION ─────────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/rate', methods=['POST'])
@login_required
def recipe_rate(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    rating = request.form.get('rating', type=int)
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Note invalide.'})

    if recipe.rating == rating:
        recipe.rating = None
        db.session.commit()
        return jsonify({'success': True, 'rating': None})

    recipe.rating = rating
    db.session.commit()
    return jsonify({'success': True, 'rating': rating})


# ── RANDOM ───────────────────────────────────────────────────
@recipes_bp.route('/recipe/random')
@login_required
def random_recipe():
    recipe_ids = [r[0] for r in Recipe.query.filter_by(
        user_id=current_user.id).with_entities(Recipe.id).all()]
    if not recipe_ids:
        flash("Créez d'abord quelques recettes !", 'warning')
        return redirect(url_for('recipes.index'))
    return redirect(url_for('recipes.recipe_detail', id=random.choice(recipe_ids)))


# ── TAGS ─────────────────────────────────────────────────────
@recipes_bp.route('/tag/<tag_name>')
@login_required
def recipes_by_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first_or_404()
    recipes = Recipe.query.filter(
        Recipe.user_id == current_user.id,
        Recipe.tags.any(Tag.id == tag.id)
    ).order_by(Recipe.created_at.desc()).all()
    return render_template('recipes_by_tag.html', tag=tag, recipes=recipes)


# ── HISTORIQUE ───────────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/cooked', methods=['POST'])
@login_required
def mark_cooked(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
    try:
        db.session.add(CookingHistory(user_id=current_user.id, recipe_id=recipe.id))
        db.session.commit()
        return jsonify({'success': True, 'message': "Ajouté à l'historique !"})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


@recipes_bp.route('/history')
@login_required
def history():
    history_entries = CookingHistory.query.filter_by(user_id=current_user.id)\
        .order_by(CookingHistory.cooked_at.desc()).all()
    return render_template('history.html', history=history_entries)


@recipes_bp.route('/history/delete/<int:entry_id>', methods=['POST'])
@login_required
def history_delete_entry(entry_id):
    entry = db.get_or_404(CookingHistory, entry_id)
    if entry.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


@recipes_bp.route('/history/clear', methods=['POST'])
@login_required
def history_clear():
    try:
        CookingHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("Historique vidé.", 'success')
    except Exception:
        db.session.rollback()
        flash("Erreur lors de la suppression.", 'danger')
    return redirect(url_for('recipes.history'))


# ── TOUTES LES RECETTES ──────────────────────────────────────
@recipes_bp.route('/all-recipes')
@login_required
def all_recipes():
    recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(
        Recipe.category, Recipe.title).all()
    categories = Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()

    recipe_data = []
    for recipe in recipes:
        total_time = (recipe.prep_time or 0) + (recipe.cook_time or 0)
        ingredients_list = [f"{ing.quantity or ''} {ing.unit} {ing.name}".strip()
                            for ing in recipe.ingredients]
        recipe_data.append({
            'id': recipe.id,
            'title': recipe.title,
            'category': recipe.category or 'Autre',
            'image': recipe.image_filename,
            'ingredients': ingredients_list,
            'total_time': total_time,
            'total_carbs': recipe.total_carbs or 0,
            'servings': recipe.servings or 4,
            'difficulty': recipe.difficulty or 'Moyen',
            'rating': recipe.rating
        })

    return render_template('all_recipes.html', recipe_data=recipe_data, categories=categories)


# ── PARTAGE PUBLIC ───────────────────────────────────────────
@recipes_bp.route('/recipe/<int:id>/share', methods=['POST'])
@login_required
def recipe_share(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    action = request.form.get('action', 'generate')
    if action == 'revoke':
        recipe.revoke_share_token()
        db.session.commit()
        return jsonify({'success': True, 'action': 'revoked'})
    else:
        if not recipe.share_token:
            recipe.generate_share_token()
            db.session.commit()
        share_url = url_for('recipes.recipe_public', token=recipe.share_token, _external=True)
        return jsonify({'success': True, 'action': 'generated', 'share_url': share_url})


@recipes_bp.route('/recette/<token>')
def recipe_public(token):
    recipe = Recipe.query.filter_by(share_token=token).first_or_404()
    return render_template('recipe_shared.html', recipe=recipe)


# ── API ──────────────────────────────────────────────────────
@recipes_bp.route('/api/recipes')
@login_required
def api_recipes():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    return jsonify([r.to_dict() for r in recipes])


@recipes_bp.route('/api/recipe/<int:id>')
@login_required
def api_recipe(id):
    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    return jsonify(recipe.to_dict())


# ── PING ─────────────────────────────────────────────────────
@recipes_bp.route('/ping')
def ping():
    return jsonify({'status': 'ok'}), 200


# ── HELPERS INTERNES ─────────────────────────────────────────
def _save_ingredients(recipe_id, form):
    names = form.getlist('ingredient_name[]')
    quantities = form.getlist('ingredient_quantity[]')
    units = form.getlist('ingredient_unit[]')
    for i, name in enumerate(names):
        if name.strip():
            qty = None
            if i < len(quantities) and quantities[i]:
                try:
                    qty = float(quantities[i])
                except ValueError:
                    qty = None
            unit = units[i] if i < len(units) else 'g'
            db.session.add(Ingredient(
                recipe_id=recipe_id, name=name.strip(), quantity=qty, unit=unit))


def _save_steps(recipe_id, form):
    instructions = form.getlist('step_instruction[]')
    durations = form.getlist('step_duration[]')
    for i, instruction in enumerate(instructions):
        if instruction.strip():
            dur = None
            if i < len(durations) and durations[i]:
                try:
                    dur = int(durations[i])
                except ValueError:
                    dur = None
            db.session.add(Step(
                recipe_id=recipe_id, order=i + 1,
                instruction=instruction.strip(), duration=dur))


def _save_tags(recipe, tags_input):
    from flask_login import current_user
    recipe.tags = []
    if tags_input:
        tag_names = list(set([t.strip() for t in tags_input.split(',') if t.strip()]))
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
            if not tag:
                tag = Tag(name=tag_name, user_id=current_user.id)
                db.session.add(tag)
            recipe.tags.append(tag)
