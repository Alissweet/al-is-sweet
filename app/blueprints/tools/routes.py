from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Recipe, Ingredient, Step, Tag, Category
from app.utils.helpers import safe_int, safe_float, safe_str
from datetime import datetime
import json
import io
import re
import difflib
import logging

tools_bp = Blueprint('tools', __name__)
logger = logging.getLogger(__name__)


# ── PDF ──────────────────────────────────────────────────────
@tools_bp.route('/recipe/<int:id>/pdf')
@login_required
def recipe_pdf(id):
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    recipe = db.get_or_404(Recipe, id)
    if recipe.user_id != current_user.id:
        flash("Accès non autorisé.", 'danger')
        return redirect(url_for('recipes.index'))

    html_string = render_template(
        'recipe_print.html', recipe=recipe,
        now=datetime.now(), base_url=request.host_url)

    font_config = FontConfiguration()
    extra_css = CSS(string="", font_config=font_config, base_url=request.host_url)
    pdf_bytes = HTML(string=html_string, base_url=request.host_url).write_pdf(
        stylesheets=[extra_css], font_config=font_config)

    safe_title = re.sub(r'[^\w\-]', '_', recipe.title)
    return Response(pdf_bytes, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename="{safe_title}.pdf"'})


# ── LISTE DE COURSES ─────────────────────────────────────────
@tools_bp.route('/shopping-list', methods=['POST'])
@login_required
def shopping_list():
    recipe_ids_raw = request.form.get('recipe_ids', '')
    if not recipe_ids_raw:
        flash("Sélectionne au moins une recette.", 'warning')
        return redirect(url_for('recipes.index'))

    try:
        recipe_ids = [int(i) for i in recipe_ids_raw.split(',') if i.strip()]
    except ValueError:
        flash("Sélection invalide.", 'danger')
        return redirect(url_for('recipes.index'))

    recipes = Recipe.query.filter(
        Recipe.id.in_(recipe_ids),
        Recipe.user_id == current_user.id
    ).all()

    if not recipes:
        flash("Aucune recette valide sélectionnée.", 'warning')
        return redirect(url_for('recipes.index'))

    consolidated = {}
    for recipe in recipes:
        for ing in recipe.ingredients:
            key = (ing.name.strip().lower(), (ing.unit or '').strip().lower())
            if key not in consolidated:
                consolidated[key] = {
                    'name': ing.name.strip(), 'unit': ing.unit or '',
                    'quantity': 0, 'has_qty': False, 'recipes': []
                }
            if ing.quantity:
                consolidated[key]['quantity'] += ing.quantity
                consolidated[key]['has_qty'] = True
            if recipe.title not in consolidated[key]['recipes']:
                consolidated[key]['recipes'].append(recipe.title)

    shopping_items = sorted(consolidated.values(), key=lambda x: x['name'].lower())
    return render_template('shopping_list.html', recipes=recipes, shopping_items=shopping_items)


# ── EXPORT SÉLECTION ─────────────────────────────────────────
@tools_bp.route('/export_selected', methods=['POST'])
@login_required
def export_selected():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données invalides'}), 400

    recipe_ids = data.get('ids', [])
    if not recipe_ids:
        return jsonify({'error': 'Aucune recette sélectionnée'}), 400
    if not all(isinstance(i, int) for i in recipe_ids):
        return jsonify({'error': 'IDs invalides'}), 400
    if len(recipe_ids) > 100:
        return jsonify({'error': 'Trop de recettes sélectionnées'}), 400

    recipes = Recipe.query.filter(
        Recipe.id.in_(recipe_ids),
        Recipe.user_id == current_user.id
    ).all()

    export_data = []
    for recipe in recipes:
        r_dict = recipe.to_dict()
        r_dict.pop('id', None)
        r_dict.pop('is_favorite', None)
        r_dict['image_filename'] = None
        for ing in r_dict.get('ingredients', []):
            ing.pop('id', None)
        for step in r_dict.get('steps', []):
            step.pop('id', None)
        export_data.append(r_dict)

    mem_file = io.BytesIO()
    mem_file.write(json.dumps(export_data, ensure_ascii=False, indent=4).encode('utf-8'))
    mem_file.seek(0)
    return send_file(mem_file, mimetype='application/json', as_attachment=True,
                     download_name='recettes_selectionnees.json')


# ── ANALYSE IMPORT ───────────────────────────────────────────
@tools_bp.route('/analyze_import', methods=['POST'])
@login_required
def analyze_import():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    try:
        imported_recipes = json.load(file)
    except Exception:
        return jsonify({'error': 'Fichier JSON invalide'}), 400

    if not isinstance(imported_recipes, list):
        return jsonify({'error': 'Format invalide : une liste de recettes est attendue'}), 400

    if len(imported_recipes) > 100:
        return jsonify({'error': 'Maximum 100 recettes par import'}), 400

    existing_recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    existing_titles = {r.title.lower(): r for r in existing_recipes}
    existing_titles_list = list(existing_titles.keys())

    new_recipes, conflicts = [], []

    for recipe in imported_recipes:
        title = recipe.get('title', '')
        if not title:
            continue
        title_lower = str(title).lower()

        if title_lower in existing_titles:
            recipe['_conflict_reason'] = 'Nom identique'
            conflicts.append(recipe)
            continue

        matches = difflib.get_close_matches(title_lower, existing_titles_list, n=1, cutoff=0.8)
        if matches:
            recipe['_conflict_reason'] = f'Très proche de "{existing_titles[matches[0]].title}"'
            conflicts.append(recipe)
        else:
            new_recipes.append(recipe)

    return jsonify({'new_recipes': new_recipes, 'conflicts': conflicts})


# ── FINALISER IMPORT ─────────────────────────────────────────
@tools_bp.route('/finalize_import', methods=['POST'])
@login_required
def finalize_import():
    data = request.get_json()
    if not data or 'recipes' not in data:
        return jsonify({'error': 'Données invalides'}), 400

    recipes_to_add = data['recipes']
    if not isinstance(recipes_to_add, list):
        return jsonify({'error': 'Données invalides'}), 400

    existing_titles = {r.title.lower() for r in Recipe.query.filter_by(user_id=current_user.id).all()}
    imported_count = 0

    try:
        for r_data in recipes_to_add:
            title = safe_str(r_data.get('title', ''), 200)
            if not title or title.lower() in existing_titles:
                continue

            new_recipe = Recipe(
                user_id=current_user.id,
                title=title,
                description=safe_str(r_data.get('description')),
                tips=safe_str(r_data.get('tips')),
                prep_time=safe_int(r_data.get('prep_time')),
                cook_time=safe_int(r_data.get('cook_time')),
                servings=safe_int(r_data.get('servings'), default=4, min_val=1, max_val=100),
                difficulty=safe_str(r_data.get('difficulty'), 50),
                category=safe_str(r_data.get('category'), 100),
                total_carbs=safe_float(r_data.get('total_carbs')),
                rating=safe_int(r_data.get('rating'), min_val=0, max_val=5),
                source=safe_str(r_data.get('source'), 500)
            )
            db.session.add(new_recipe)
            db.session.flush()

            for ing_data in r_data.get('ingredients', []):
                db.session.add(Ingredient(
                    recipe_id=new_recipe.id,
                    name=safe_str(ing_data.get('name', 'Ingrédient inconnu'), 200),
                    quantity=safe_float(ing_data.get('quantity')),
                    unit=safe_str(ing_data.get('unit'), 50)
                ))

            for step_data in r_data.get('steps', []):
                db.session.add(Step(
                    recipe_id=new_recipe.id,
                    order=safe_int(step_data.get('order'), default=1),
                    instruction=safe_str(step_data.get('instruction', ''), 5000),
                    duration=safe_int(step_data.get('duration'))
                ))

            for tag_name in r_data.get('tags', []):
                clean_tag = safe_str(tag_name, 50)
                if clean_tag:
                    tag = Tag.query.filter_by(name=clean_tag, user_id=current_user.id).first()
                    if not tag:
                        tag = Tag(name=clean_tag, user_id=current_user.id)
                        db.session.add(tag)
                    new_recipe.tags.append(tag)

            imported_count += 1
            existing_titles.add(title.lower())

        db.session.commit()
        return jsonify({'message': f'{imported_count} recette(s) importée(s) avec succès !'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur importation: {e}")
        return jsonify({'error': "Erreur lors de l'enregistrement."}), 500