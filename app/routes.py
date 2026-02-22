from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from app import db
from app.models import Recipe, Ingredient, Step, Category, Tag, CookingHistory
from app.forms import RecipeForm
from datetime import datetime
from sqlalchemy import func, case
import json
import os
import uuid
import logging
import cloudinary
import cloudinary.uploader
import random

main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


# ============================================================
#  UTILITAIRES
# ============================================================

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_image(file):
    if file and allowed_file(file.filename):
        if current_app.config.get('CLOUDINARY_URL'):
            try:
                cloudinary.config(cloudinary_url=current_app.config['CLOUDINARY_URL'])
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="al_is_sweet_recipes",
                    allowed_formats=['jpg', 'png', 'jpeg', 'webp'],
                    transformation=[{'width': 1000, 'crop': "limit"}]
                )
                return upload_result.get('secure_url')
            except Exception as e:
                logger.error(f"Erreur Upload Cloudinary: {e}")
                return None
        else:
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return filename
    return None


# ============================================================
#  ROUTES PRINCIPALES
# ============================================================

@main.route('/')
@login_required
def index():
    """Page d'accueil avec filtres combinés et tri"""
    page = request.args.get('page', 1, type=int)
    
    # Récupération des filtres
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    max_time = request.args.get('max_time', type=int)
    sort = request.args.get('sort', 'date_desc')

    tag = request.args.get('tag', '')

    # Base de la requête
    query = Recipe.query.filter_by(user_id=current_user.id)
    
    # --- FILTRES ---
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

    # --- TRI ---
    if sort == 'alpha_asc':
        query = query.order_by(Recipe.title.asc())
    elif sort == 'time_asc':
        query = query.order_by((func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)).asc())
    elif sort == 'difficulty_asc':
        # ✅ CORRECTION : Syntaxe dictionnaire pour SQLAlchemy 2.x
        difficulty_order = case(
            {
                'Facile': 1,
                'Moyen': 2,
                'Difficile': 3
            },
            value=Recipe.difficulty,
            else_=4
        )
        query = query.order_by(difficulty_order.asc())
    elif sort == 'date_asc':
        query = query.order_by(Recipe.created_at.asc())
    else: # date_desc
        query = query.order_by(Recipe.created_at.desc())

    # Pagination
    recipes = query.paginate(page=page, per_page=9, error_out=False)
    
    categories = [c.name for c in Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()]

    available_tags = Tag.query.filter_by(user_id=current_user.id)        .join(Tag.recipes).filter(Recipe.user_id == current_user.id)        .distinct().order_by(Tag.name).all()

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


@main.route('/recipe/<int:id>')
@login_required
def recipe_detail(id):
    recipe = Recipe.query.get_or_404(id)
    if recipe.user_id != current_user.id:
        flash("Vous n'avez pas accès à cette recette.", 'danger')
        return redirect(url_for('main.index'))

    similar_recipes = []
    if recipe.tags:
        tag_ids = [t.id for t in recipe.tags]
        similar_recipes = Recipe.query.filter(
            Recipe.user_id == current_user.id,
            Recipe.id != recipe.id,
            Recipe.tags.any(Tag.id.in_(tag_ids))
        ).order_by(Recipe.created_at.desc()).limit(3).all()

    return render_template('recipe_detail.html', recipe=recipe, similar_recipes=similar_recipes)


# ============================================================
#  CRÉATION DE RECETTE
# ============================================================

@main.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def recipe_new():
    form = RecipeForm()

    if request.method == 'POST':
        try:
            servings = request.form.get('servings', 4, type=int)
            if servings <= 0:
                servings = 4

            total_carbs = float(request.form.get('total_carbs', 0))
            if total_carbs < 0:
                total_carbs = 0

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

            ingredient_names = request.form.getlist('ingredient_name[]')
            ingredient_quantities = request.form.getlist('ingredient_quantity[]')
            ingredient_units = request.form.getlist('ingredient_unit[]')

            for i, name in enumerate(ingredient_names):
                if name.strip():
                    qty = None
                    if i < len(ingredient_quantities) and ingredient_quantities[i]:
                        try:
                            qty = float(ingredient_quantities[i])
                        except ValueError:
                            qty = None
                    unit = ingredient_units[i] if i < len(ingredient_units) else 'g'
                    db.session.add(Ingredient(
                        recipe_id=recipe.id,
                        name=name.strip(),
                        quantity=qty,
                        unit=unit
                    ))

            step_instructions = request.form.getlist('step_instruction[]')
            step_durations = request.form.getlist('step_duration[]')

            for i, instruction in enumerate(step_instructions):
                if instruction.strip():
                    duration = None
                    if i < len(step_durations) and step_durations[i]:
                        try:
                            duration = int(step_durations[i])
                        except ValueError:
                            duration = None
                    db.session.add(Step(
                        recipe_id=recipe.id,
                        order=i + 1,
                        instruction=instruction.strip(),
                        duration=duration
                    ))
            # GESTION DES TAGS
            tags_input = request.form.get('tags', '')
            recipe.tags = []
            if tags_input:
                # Séparation par virgule et nettoyage
                tag_names = list(set([t.strip() for t in tags_input.split(',') if t.strip()]))
                
                for tag_name in tag_names:
                    # Chercher si le tag existe déjà POUR CET UTILISATEUR
                    tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
                    
                    if not tag:
                        # Création du tag lié à l'utilisateur
                        tag = Tag(name=tag_name, user_id=current_user.id)
                        db.session.add(tag)
                    
                    recipe.tags.append(tag)

            db.session.commit()
            flash('Recette créée avec succès! 🎉', 'success')
            return redirect(url_for('main.recipe_detail', id=recipe.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur création recette: {e}")
            flash(f'Erreur lors de la création : {str(e)}', 'danger')

    categories = [c.name for c in Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()]
    return render_template('recipe_form.html', form=form, recipe=None, categories=categories)


# ============================================================
#  MODIFICATION DE RECETTE
# ============================================================

@main.route('/recipe/<int:id>/edit', methods=['GET', 'POST'])
@login_required  # ✅ CORRIGÉ : ajouté
def recipe_edit(id):
    recipe = Recipe.query.get_or_404(id)

    # ✅ CORRIGÉ : redirection si pas propriétaire
    if recipe.user_id != current_user.id:
        flash('Vous ne pouvez pas modifier cette recette.', 'danger')
        return redirect(url_for('main.index'))

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
                    if recipe.image_filename:
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

            ingredient_names = request.form.getlist('ingredient_name[]')
            ingredient_quantities = request.form.getlist('ingredient_quantity[]')
            ingredient_units = request.form.getlist('ingredient_unit[]')

            for i, name in enumerate(ingredient_names):
                if name.strip():
                    qty = None
                    if i < len(ingredient_quantities):
                        qty_val = ingredient_quantities[i]
                        if qty_val and qty_val.strip():
                            try:
                                qty = float(qty_val)
                            except ValueError:
                                qty = None
                    unit = ingredient_units[i] if i < len(ingredient_units) else 'g'
                    db.session.add(Ingredient(
                        recipe_id=recipe.id,
                        name=name.strip(),
                        quantity=qty,
                        unit=unit
                    ))

            step_instructions = request.form.getlist('step_instruction[]')
            step_durations = request.form.getlist('step_duration[]')

            for i, instruction in enumerate(step_instructions):
                if instruction.strip():
                    dur = None
                    if i < len(step_durations):
                        dur_val = step_durations[i]
                        if dur_val and dur_val.strip():
                            try:
                                dur = int(dur_val)
                            except ValueError:
                                dur = None
                    db.session.add(Step(
                        recipe_id=recipe.id,
                        order=i + 1,
                        instruction=instruction.strip(),
                        duration=dur
                    ))
            # GESTION DES TAGS
            tags_input = request.form.get('tags', '')
            recipe.tags = []
            if tags_input:
                # Séparation par virgule et nettoyage
                tag_names = list(set([t.strip() for t in tags_input.split(',') if t.strip()]))
                
                for tag_name in tag_names:
                    # Chercher si le tag existe déjà POUR CET UTILISATEUR
                    tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
                    
                    if not tag:
                        # Création du tag lié à l'utilisateur
                        tag = Tag(name=tag_name, user_id=current_user.id)
                        db.session.add(tag)
                    
                    recipe.tags.append(tag)
                    
            db.session.commit()
            flash('Recette modifiée avec succès! ✨', 'success')
            return redirect(url_for('main.recipe_detail', id=recipe.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur modification recette: {e}")
            flash(f'Erreur lors de la sauvegarde : {str(e)}', 'danger')
            return render_template('recipe_form.html', form=form, recipe=recipe, categories=categories)

    return render_template('recipe_form.html', form=form, recipe=recipe, categories=categories)


# ============================================================
#  SUPPRESSION DE RECETTE
# ============================================================

@main.route('/recipe/<int:id>/delete', methods=['POST'])
@login_required  # ✅ CORRIGÉ : ajouté
def recipe_delete(id):
    recipe = Recipe.query.get_or_404(id)

    # ✅ CORRIGÉ : vérification du propriétaire ajoutée
    if recipe.user_id != current_user.id:
        flash('Vous ne pouvez pas supprimer cette recette.', 'danger')
        return redirect(url_for('main.index'))

    if recipe.image_filename:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Erreur suppression image: {e}")

    db.session.delete(recipe)
    db.session.commit()
    flash('Recette supprimée avec succès!', 'success')
    return redirect(url_for('main.index'))



# ============================================================
#  FONCTIONNALITÉS PREMIUM (Random, Tags, History)
# ============================================================

@main.route('/recipe/random')
@login_required
def random_recipe():
    """Redirige vers une recette aléatoire de l'utilisateur (Optimisé)"""
    # ✅ OPTIMISATION : On ne charge que les IDs, pas les objets entiers
    recipe_ids = [r[0] for r in Recipe.query.filter_by(user_id=current_user.id).with_entities(Recipe.id).all()]
    
    if not recipe_ids:
        flash("Créez d'abord quelques recettes !", 'warning')
        return redirect(url_for('main.index'))
    
    random_id = random.choice(recipe_ids)
    return redirect(url_for('main.recipe_detail', id=random_id))


@main.route('/tag/<tag_name>')
@login_required
def recipes_by_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first_or_404()
    recipes = Recipe.query.filter(
        Recipe.user_id == current_user.id,
        Recipe.tags.any(Tag.id == tag.id)
    ).order_by(Recipe.created_at.desc()).all()
    return render_template('recipes_by_tag.html', tag=tag, recipes=recipes)


@main.route('/recipe/<int:id>/cooked', methods=['POST'])
@login_required
def mark_cooked(id):
    """Marque une recette comme cuisinée aujourd'hui"""
    recipe = Recipe.query.get_or_404(id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
    try:
        entry = CookingHistory(user_id=current_user.id, recipe_id=recipe.id)
        db.session.add(entry)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Ajouté à l\'historique ! 📅'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


@main.route('/history')
@login_required
def history():
    """Page d'historique culinaire"""
    # Récupère l'historique trié par date décroissante
    history_entries = CookingHistory.query.filter_by(user_id=current_user.id)\
        .order_by(CookingHistory.cooked_at.desc()).all()
        
    # On groupe par mois pour l'affichage (facultatif mais joli)
    return render_template('history.html', history=history_entries)


@main.route('/history/delete/<int:entry_id>', methods=['POST'])
@login_required
def history_delete_entry(entry_id):
    entry = CookingHistory.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


@main.route('/history/clear', methods=['POST'])
@login_required
def history_clear():
    try:
        CookingHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("Historique vidé avec succès.", 'success')
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de la suppression.", 'danger')
    return redirect(url_for('main.history'))


# ============================================================
#  API — PROTÉGÉES
# ============================================================

@main.route('/api/recipes')
@login_required  # ✅ CORRIGÉ
def api_recipes():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    return jsonify([recipe.to_dict() for recipe in recipes])


@main.route('/api/recipe/<int:id>')
@login_required  # ✅ CORRIGÉ
def api_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    if recipe.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    return jsonify(recipe.to_dict())


# ============================================================
#  EXPORT / IMPORT — PROTÉGÉS
# ============================================================

@main.route('/admin/export')
@login_required  # ✅ CORRIGÉ
def export_data():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    data = [r.to_dict() for r in recipes]
    response = jsonify(data)
    response.headers.set('Content-Disposition', 'attachment',
                         filename=f'recipes_backup_{datetime.now().strftime("%Y%m%d")}.json')
    return response


@main.route('/admin/import', methods=['POST'])
@login_required  # ✅ CORRIGÉ
def import_data():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('main.index'))

    file = request.files['file']
    try:
        data = json.load(file)

        if not isinstance(data, list):
            flash('Format JSON invalide : doit être une liste de recettes', 'danger')
            return redirect(url_for('main.index'))

        count = 0
        for item in data:
            if not isinstance(item, dict) or 'title' not in item:
                logger.warning("Recette ignorée : structure invalide")
                continue

            exists = Recipe.query.filter_by(
                title=item['title'], user_id=current_user.id).first()

            if not exists:
                recipe = Recipe(
                    user_id=current_user.id,  # ✅ CORRIGÉ
                    title=item['title'],
                    description=item.get('description'),
                    tips=item.get('tips'),
                    prep_time=item.get('prep_time', 0),
                    cook_time=item.get('cook_time', 0),
                    servings=max(1, item.get('servings', 4)),
                    difficulty=item.get('difficulty'),
                    category=item.get('category'),
                    total_carbs=max(0, float(item.get('total_carbs', 0))),
                    image_filename=item.get('image_filename')
                )
                db.session.add(recipe)
                db.session.flush()

                for ing_data in item.get('ingredients', []):
                    if isinstance(ing_data, dict) and 'name' in ing_data:
                        db.session.add(Ingredient(
                            recipe_id=recipe.id,
                            name=ing_data['name'],
                            quantity=ing_data.get('quantity'),
                            unit=ing_data.get('unit', 'g')
                        ))

                for step_data in item.get('steps', []):
                    if isinstance(step_data, dict) and 'instruction' in step_data:
                        db.session.add(Step(
                            recipe_id=recipe.id,
                            order=step_data.get('order', 1),
                            instruction=step_data['instruction'],
                            duration=step_data.get('duration')
                        ))
                count += 1

        db.session.commit()
        flash(f'{count} nouvelles recettes importées avec succès !', 'success')

    except json.JSONDecodeError:
        flash('Fichier JSON invalide', 'danger')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import: {e}")
        flash(f"Erreur lors de l'import : {str(e)}", 'danger')

    return redirect(url_for('main.index'))


# ============================================================
#  GESTION DES CATÉGORIES — PROTÉGÉES
# ============================================================

@main.route('/settings/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('category_name')
    if name and name.strip():
        name = name.strip()
        if len(name) > 100:
            return jsonify({'success': False, 'message': 'Nom trop long (max 100 caractères).'})

        exists = Category.query.filter_by(name=name, user_id=current_user.id).first()
        if not exists:
            try:
                new_cat = Category(name=name, user_id=current_user.id)
                db.session.add(new_cat)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': f'Famille "{name}" ajoutée !',
                    'category': {'id': new_cat.id, 'name': new_cat.name}
                })
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erreur ajout catégorie: {e}")
                return jsonify({'success': False, 'message': "Erreur lors de l'ajout."})
        else:
            return jsonify({'success': False, 'message': 'Cette famille existe déjà.'})

    return jsonify({'success': False, 'message': 'Nom de catégorie manquant.'})


@main.route('/settings/category/delete/<int:id>', methods=['POST'])
@login_required  # ✅ CORRIGÉ
def delete_category(id):
    cat = Category.query.get_or_404(id)
    if cat.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    cat_name = cat.name
    orphan_recipes = Recipe.query.filter_by(
        category=cat_name, user_id=current_user.id).all()
    for recipe in orphan_recipes:
        recipe.category = 'Autre'

    try:
        db.session.delete(cat)
        db.session.commit()
        message = f'Famille "{cat_name}" supprimée.'
        if orphan_recipes:
            message += f' {len(orphan_recipes)} recette(s) déplacée(s) vers "Autre".'
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur suppression catégorie: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression.'})


@main.route('/settings/category/edit/<int:id>', methods=['POST'])
@login_required  # ✅ CORRIGÉ
def edit_category(id):
    cat = Category.query.get_or_404(id)
    if cat.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    new_name = request.form.get('new_name')

    if new_name and new_name.strip() and new_name.strip() != cat.name:
        new_name = new_name.strip()

        if len(new_name) > 100:
            return jsonify({'success': False, 'message': 'Nom trop long (max 100 caractères).'})

        if Category.query.filter_by(name=new_name, user_id=current_user.id).first():
            return jsonify({'success': False, 'message': 'Ce nom de famille existe déjà.'})

        try:
            old_name = cat.name
            cat.name = new_name
            recipes_to_update = Recipe.query.filter_by(
                category=old_name, user_id=current_user.id).all()
            for recipe in recipes_to_update:
                recipe.category = new_name

            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Famille renommée en "{new_name}" ({len(recipes_to_update)} recettes mises à jour).',
                'category': {'id': cat.id, 'name': new_name}
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur modification catégorie: {e}")
            return jsonify({'success': False, 'message': 'Erreur lors de la modification.'})

    return jsonify({'success': False, 'message': 'Nouveau nom invalide ou identique.'})


# ============================================================
#  INITIALISATION DES CATÉGORIES PAR DÉFAUT
# ============================================================

@main.route('/init-categories')
@login_required
def init_categories():
    defaults = ['Pâtisserie', 'Viennoiserie', 'Confiserie', 'Dessert Glacé',
                'Gâteau', 'Tarte', 'Boisson', 'Autre']
    count = 0
    for name in defaults:
        if not Category.query.filter_by(name=name, user_id=current_user.id).first():
            db.session.add(Category(name=name, user_id=current_user.id))
            count += 1

    try:
        db.session.commit()
        if count > 0:
            flash(f'{count} catégories par défaut ajoutées à votre compte !', 'success')
        else:
            flash('Vous aviez déjà toutes les catégories par défaut.', 'info')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur init catégories: {e}")
        flash("Erreur lors de l'initialisation.", 'danger')

    return redirect(url_for('main.index'))


# ============================================================
#  PAGE TOUTES LES RECETTES
# ============================================================

@main.route('/all-recipes')
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

    return render_template('all_recipes.html',
                           recipe_data=recipe_data,
                           categories=categories)


# ============================================================
#  PING — Pour UptimeRobot
# ============================================================

@main.route('/ping')
def ping():
    """Route légère pour UptimeRobot — maintient Render actif"""
    return jsonify({'status': 'ok'}), 200


# ============================================================
#  PARTAGER RECETTE
# ============================================================
@main.route('/recipe/<int:id>/share', methods=['POST'])
@login_required
def recipe_share(id):
    recipe = Recipe.query.get_or_404(id)
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
        share_url = url_for('main.recipe_public', token=recipe.share_token, _external=True)
        return jsonify({'success': True, 'action': 'generated', 'share_url': share_url})

@main.route('/recette/<token>')
def recipe_public(token):
    recipe = Recipe.query.filter_by(share_token=token).first_or_404()
    return render_template('recipe_shared.html', recipe=recipe)


# ===============================================================
# IMPRIMER RECETTE INDIVIDUELLE
# ===============================================================
@main.route('/recipe/<int:id>/pdf')
@login_required
def recipe_pdf(id):
    recipe = Recipe.query.get_or_404(id)

    # Sécurité : seul le propriétaire peut télécharger
    if recipe.user_id != current_user.id:
        flash("Accès non autorisé.", 'danger')
        return redirect(url_for('main.index'))

    # Rendre le template HTML
    html_string = render_template('recipe_print.html', recipe=recipe)

    # Générer le PDF avec WeasyPrint
    font_config = FontConfiguration()
    pdf_bytes = HTML(
        string=html_string,
        base_url=request.host_url          # nécessaire pour charger les images locales
    ).write_pdf(
        font_config=font_config
    )

    # Nom de fichier propre (sans espaces ni caractères spéciaux)
    import re
    safe_title = re.sub(r'[^\w\-]', '_', recipe.title)

    # Retourner le PDF en téléchargement direct
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'inline; filename="{safe_title}.pdf"'
            # 'inline' = s'ouvre dans le navigateur
            # Remplacer par 'attachment' pour forcer le téléchargement
        }
    )


# ============================================================
#  NOTATION DES RECETTES
# ============================================================
@main.route('/recipe/<int:id>/rate', methods=['POST'])
@login_required
def recipe_rate(id):
    recipe = Recipe.query.get_or_404(id)
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    rating = request.form.get('rating', type=int)
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Note invalide.'})

    # Si on reclique sur la même note → on efface (toggle)
    if recipe.rating == rating:
        recipe.rating = None
        db.session.commit()
        return jsonify({'success': True, 'rating': None})

    recipe.rating = rating
    db.session.commit()
    return jsonify({'success': True, 'rating': rating})

# ============================================================
#  LISTE DE COURSES CONSOLIDÉE
# ============================================================
@main.route('/shopping-list', methods=['POST'])
@login_required
def shopping_list():
    # Récupérer les IDs des recettes sélectionnées
    recipe_ids_raw = request.form.get('recipe_ids', '')
    if not recipe_ids_raw:
        flash("Sélectionne au moins une recette.", 'warning')
        return redirect(url_for('main.index'))

    try:
        recipe_ids = [int(i) for i in recipe_ids_raw.split(',') if i.strip()]
    except ValueError:
        flash("Sélection invalide.", 'danger')
        return redirect(url_for('main.index'))

    # Charger les recettes en vérifiant l'appartenance
    recipes = Recipe.query.filter(
        Recipe.id.in_(recipe_ids),
        Recipe.user_id == current_user.id
    ).all()

    if not recipes:
        flash("Aucune recette valide sélectionnée.", 'warning')
        return redirect(url_for('main.index'))

    # Consolider les ingrédients
    # Clé : (nom_normalisé, unité) → cumul des quantités
    consolidated = {}
    for recipe in recipes:
        for ing in recipe.ingredients:
            name_key = ing.name.strip().lower()
            unit_key = (ing.unit or '').strip().lower()
            key = (name_key, unit_key)

            if key not in consolidated:
                consolidated[key] = {
                    'name': ing.name.strip(),
                    'unit': ing.unit or '',
                    'quantity': 0,
                    'has_qty': False,
                    'recipes': []
                }
            if ing.quantity:
                consolidated[key]['quantity'] += ing.quantity
                consolidated[key]['has_qty'] = True
            if recipe.title not in consolidated[key]['recipes']:
                consolidated[key]['recipes'].append(recipe.title)

    # Trier par nom
    shopping_items = sorted(consolidated.values(), key=lambda x: x['name'].lower())

    return render_template('shopping_list.html',
                           recipes=recipes,
                           shopping_items=shopping_items)


# ============================================================
#  GESTION DES FAVORIS
# ============================================================
@main.route('/recipe/<int:id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(id):
    recipe = Recipe.query.get_or_404(id)
    
    # Sécurité : Vérifier que la recette appartient à l'utilisateur
    if recipe.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée'}), 403
        
    # Bascule l'état
    recipe.is_favorite = not recipe.is_favorite
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'is_favorite': recipe.is_favorite,
            'message': 'Ajouté aux favoris ❤️' if recipe.is_favorite else 'Retiré des favoris'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur favori: {e}")
        return jsonify({'success': False, 'message': 'Erreur technique'}), 500


# ============================================================
#  CONTEXT PROCESSOR
# ============================================================

@main.context_processor
def inject_categories():
    def get_all_categories():
        try:
            if current_user.is_authenticated:
                return Category.query.filter_by(
                    user_id=current_user.id).order_by(Category.name).all()
            return []
        except Exception as e:
            logger.error(f"Erreur context processor: {e}")
            return []
    return dict(get_all_categories=get_all_categories)