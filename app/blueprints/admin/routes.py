from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Recipe, Category, Ingredient, Step, Tag
from app.utils.helpers import safe_str
from datetime import datetime
import json
import io
import difflib
import logging
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


# ── DASHBOARD ────────────────────────────────────────────────
@admin_bp.route('/')
@login_required
def dashboard():
    stats = {
        'total_recipes': Recipe.query.filter_by(user_id=current_user.id).count(),
        'total_categories': Category.query.filter_by(user_id=current_user.id).count(),
        'total_tags': Tag.query.filter_by(user_id=current_user.id).count(),
        'total_favorites': Recipe.query.filter_by(
            user_id=current_user.id, is_favorite=True).count(),
    }
    categories = Category.query.filter_by(
        user_id=current_user.id).order_by(Category.name).all()
    return render_template('admin/dashboard.html', stats=stats, categories=categories)


# ── CATÉGORIES ───────────────────────────────────────────────
@admin_bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('category_name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Nom manquant.'})
    if len(name) > 100:
        return jsonify({'success': False, 'message': 'Nom trop long (max 100 caractères).'})

    if Category.query.filter_by(name=name, user_id=current_user.id).first():
        return jsonify({'success': False, 'message': 'Cette famille existe déjà.'})

    try:
        cat = Category(name=name, user_id=current_user.id)
        db.session.add(cat)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Famille "{name}" ajoutée !',
                        'category': {'id': cat.id, 'name': cat.name}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': "Erreur lors de l'ajout."})


@admin_bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    cat = db.get_or_404(Category, id)
    if cat.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    cat_name = cat.name
    orphan_recipes = Recipe.query.filter_by(category=cat_name, user_id=current_user.id).all()
    for recipe in orphan_recipes:
        recipe.category = 'Autre'

    try:
        db.session.delete(cat)
        db.session.commit()
        msg = f'Famille "{cat_name}" supprimée.'
        if orphan_recipes:
            msg += f' {len(orphan_recipes)} recette(s) déplacée(s) vers "Autre".'
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression.'})


@admin_bp.route('/category/edit/<int:id>', methods=['POST'])
@login_required
def edit_category(id):
    cat = db.get_or_404(Category, id)
    if cat.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Action non autorisée.'}), 403

    new_name = request.form.get('new_name', '').strip()
    if not new_name or new_name == cat.name:
        return jsonify({'success': False, 'message': 'Nouveau nom invalide ou identique.'})
    if len(new_name) > 100:
        return jsonify({'success': False, 'message': 'Nom trop long.'})
    if Category.query.filter_by(name=new_name, user_id=current_user.id).first():
        return jsonify({'success': False, 'message': 'Ce nom existe déjà.'})

    try:
        old_name = cat.name
        cat.name = new_name
        for recipe in Recipe.query.filter_by(category=old_name, user_id=current_user.id).all():
            recipe.category = new_name
        db.session.commit()
        return jsonify({'success': True,
                        'message': f'Famille renommée en "{new_name}".',
                        'category': {'id': cat.id, 'name': new_name}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erreur lors de la modification.'})


# ── INIT CATÉGORIES PAR DÉFAUT ───────────────────────────────
@admin_bp.route('/init-categories')
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
        flash(f'{count} catégories ajoutées.' if count else 'Catégories déjà présentes.', 'info')
    except Exception:
        db.session.rollback()
        flash("Erreur lors de l'initialisation.", 'danger')
    return redirect(url_for('admin.dashboard'))


# ── EXPORT COMPLET ───────────────────────────────────────────
@admin_bp.route('/export')
@login_required
def export_data():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    data = [r.to_dict() for r in recipes]
    mem_file = io.BytesIO()
    mem_file.write(json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8'))
    mem_file.seek(0)
    return send_file(mem_file, mimetype='application/json', as_attachment=True,
                     download_name=f'backup_{datetime.now().strftime("%Y%m%d")}.json')


# ── IMPORT LEGACY (ancien /admin/import) ─────────────────────
@admin_bp.route('/import', methods=['POST'])
@login_required
def import_data():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('admin.dashboard'))

    file = request.files['file']
    try:
        data = json.load(file)
        if not isinstance(data, list):
            flash('Format JSON invalide', 'danger')
            return redirect(url_for('admin.dashboard'))

        count = 0
        for item in data:
            if not isinstance(item, dict) or 'title' not in item:
                continue
            if not Recipe.query.filter_by(title=item['title'], user_id=current_user.id).first():
                recipe = Recipe(
                    user_id=current_user.id,
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
                            recipe_id=recipe.id, name=ing_data['name'],
                            quantity=ing_data.get('quantity'), unit=ing_data.get('unit', 'g')))

                for step_data in item.get('steps', []):
                    if isinstance(step_data, dict) and 'instruction' in step_data:
                        db.session.add(Step(
                            recipe_id=recipe.id, order=step_data.get('order', 1),
                            instruction=step_data['instruction'],
                            duration=step_data.get('duration')))
                count += 1

        db.session.commit()
        flash(f'{count} recettes importées.', 'success')

    except json.JSONDecodeError:
        flash('Fichier JSON invalide', 'danger')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import: {e}")
        flash(f"Erreur : {str(e)}", 'danger')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reseed-ciqual-temp')
def reseed_ciqual_temp():
    secret = request.args.get('key')
    if secret != os.environ.get('RESEED_SECRET'):
        return "Non autorisé", 403

    try:
        from app.models import CiqualFood
        from app import db
        import csv

        CiqualFood.query.delete()
        db.session.commit()

        csv_path = os.path.join(current_app.root_path, 'static', 'data', 'ciqual.csv')

        if not os.path.exists(csv_path):
            return f"❌ Fichier introuvable à ce chemin : {csv_path}", 500

        GLUCIDES_KEY = 'Glucides\n(g\n100 g)'

        def parse_carbs(raw):
            val = (raw or '').strip()
            if not val or val == '-':
                return 0.0
            if val.lower() == 'traces':
                return 0.05
            if val.startswith('<'):
                val = val.replace('<', '').strip()
            val = val.replace(',', '.')
            try:
                return float(val)
            except ValueError:
                return 0.0

        foods = []
        skipped = 0
        with open(csv_path, 'r', encoding='latin-1') as f:
            reader = csv.DictReader(f, delimiter=';')
            if GLUCIDES_KEY not in reader.fieldnames:
                return f"❌ Colonne absente. Colonnes trouvées : {reader.fieldnames}", 500
            for row in reader:
                name = row.get('alim_nom_fr', '').strip()
                if not name:
                    skipped += 1
                    continue
                carbs = parse_carbs(row.get(GLUCIDES_KEY, ''))
                foods.append(CiqualFood(name=name, carbs_per_100g=carbs))

        if foods:
            db.session.bulk_save_objects(foods)
            db.session.commit()

        return f"✅ {len(foods)} aliments réimportés, {skipped} ignorés."

    except Exception as e:
        import traceback
        return f"<pre>❌ Erreur : {repr(e)}\n\n{traceback.format_exc()}</pre>", 500