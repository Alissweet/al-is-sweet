from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Recipe, Ingredient, Step, Category
from app.forms import RecipeForm
from datetime import datetime
import json
import os
import uuid
import logging
import cloudinary
import cloudinary.uploader

main = Blueprint('main', __name__)

# Configuration du logger pour mieux tracer les erreurs
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_image(file):
    if file and allowed_file(file.filename):
        # MODE CLOUD (Si configuré dans le .env)
        if current_app.config.get('CLOUDINARY_URL'):
            try:
                # Configuration automatique via la variable d'env
                cloudinary.config(cloudinary_url=current_app.config['CLOUDINARY_URL'])
                
                # Upload vers Cloudinary
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="al_is_sweet_recipes", # Nom du dossier dans le cloud
                    allowed_formats=['jpg', 'png', 'jpeg', 'webp'],
                    transformation=[
                        {'width': 1000, 'crop': "limit"} # Optimisation auto
                    ]
                )
                # On retourne l'URL complète (https://...)
                return upload_result.get('secure_url')
            except Exception as e:
                logger.error(f"Erreur Upload Cloudinary: {e}")
                return None
        
        # MODE LOCAL (Fallback si pas d'internet ou pas de clé)
        else:
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return filename
    return None


@main.route('/')
@login_required
def index():
    """Page d'accueil avec toutes les recettes"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = Recipe.query.filter_by(user_id=current_user.id)
    
    if category:
        query = query.filter(Recipe.category == category)
    
    if search:
        query = query.filter(Recipe.title.ilike(f'%{search}%'))
    
    recipes = query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=9, error_out=False
    )
    
    # ✅ CORRIGÉ : Suppression de la ligne inutile
    categories = [c.name for c in Category.query.order_by(Category.name).all()]
    
    return render_template('index.html', 
                         recipes=recipes, 
                         categories=categories,
                         current_category=category,
                         search=search)


@main.route('/recipe/<int:id>')
@login_required
def recipe_detail(id):
    """Détail d'une recette"""
    recipe = Recipe.query.get_or_404(id)
    return render_template('recipe_detail.html', recipe=recipe)


@main.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def recipe_new():
    """Créer une nouvelle recette"""
    form = RecipeForm()
    
    if request.method == 'POST':
        try:
            # ✅ AJOUTÉ : Validation des données
            servings = request.form.get('servings', 4, type=int)
            if servings <= 0:
                servings = 4
            
            total_carbs = float(request.form.get('total_carbs', 0))
            if total_carbs < 0:
                total_carbs = 0
            
            # Créer la recette
            recipe = Recipe(
                user_id=current_user.id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                tips=request.form.get('tips'),
                prep_time=request.form.get('prep_time', type=int),
                cook_time=request.form.get('cook_time', type=int),
                servings=servings,
                difficulty=request.form.get('difficulty'),
                category=request.form.get('category'),
                total_carbs=total_carbs
            )
            
            # Gérer l'upload de l'image
            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    filename = save_image(file)
                    if filename:
                        recipe.image_filename = filename
            
            db.session.add(recipe)
            db.session.flush()  # Pour obtenir l'ID de la recette
            
            # Ajouter les ingrédients
            ingredient_names = request.form.getlist('ingredient_name[]')
            ingredient_quantities = request.form.getlist('ingredient_quantity[]')
            ingredient_units = request.form.getlist('ingredient_unit[]')
            
            for i, name in enumerate(ingredient_names):
                if name.strip():
                    # ✅ CORRIGÉ : Vérification des index
                    qty = None
                    if i < len(ingredient_quantities) and ingredient_quantities[i]:
                        try:
                            qty = float(ingredient_quantities[i])
                        except ValueError:
                            qty = None
                    
                    unit = ingredient_units[i] if i < len(ingredient_units) else 'g'
                    
                    ingredient = Ingredient(
                        recipe_id=recipe.id,
                        name=name.strip(),
                        quantity=qty,
                        unit=unit
                    )
                    db.session.add(ingredient)
            
            # Ajouter les étapes
            step_instructions = request.form.getlist('step_instruction[]')
            step_durations = request.form.getlist('step_duration[]')
            
            for i, instruction in enumerate(step_instructions):
                if instruction.strip():
                    # ✅ CORRIGÉ : Vérification des index
                    duration = None
                    if i < len(step_durations) and step_durations[i]:
                        try:
                            duration = int(step_durations[i])
                        except ValueError:
                            duration = None
                    
                    step = Step(
                        recipe_id=recipe.id,
                        order=i + 1,
                        instruction=instruction.strip(),
                        duration=duration
                    )
                    db.session.add(step)
            
            db.session.commit()
            flash('Recette créée avec succès! 🎉', 'success')
            return redirect(url_for('main.recipe_detail', id=recipe.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur création recette: {e}")
            flash(f'Erreur lors de la création : {str(e)}', 'danger')
    
    categories = [c.name for c in Category.query.order_by(Category.name).all()]
    return render_template('recipe_form.html', form=form, recipe=None, categories=categories)


@main.route('/recipe/<int:id>/edit', methods=['GET', 'POST'])
def recipe_edit(id):
    """Modifier une recette existante"""
    recipe = Recipe.query.get_or_404(id)
    if recipe.user_id != current_user.id:
        flash('Vous ne pouvez pas modifier cette recette.', 'danger')
    form = RecipeForm(obj=recipe)
    
    categories = [c.name for c in Category.query.order_by(Category.name).all()]
    
    if request.method == 'POST':
        try:
            # Mise à jour des champs texte
            recipe.title = request.form.get('title')
            recipe.description = request.form.get('description')
            recipe.tips = request.form.get('tips')
            
            # ✅ AMÉLIORÉ : Validation des champs numériques
            recipe.prep_time = max(0, request.form.get('prep_time', type=int) or 0)
            recipe.cook_time = max(0, request.form.get('cook_time', type=int) or 0)
            recipe.servings = max(1, request.form.get('servings', 4, type=int))
            
            # Sélecteurs
            recipe.difficulty = request.form.get('difficulty')
            recipe.category = request.form.get('category')
            
            # Gestion sécurisée des glucides (float)
            try:
                recipe.total_carbs = max(0, float(request.form.get('total_carbs', 0)))
            except ValueError:
                recipe.total_carbs = 0.0
            
            # Gérer l'upload de l'image
            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    # Supprimer l'ancienne image
                    if recipe.image_filename:
                        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
                        if os.path.exists(old_path):
                            try:
                                os.remove(old_path)
                            except Exception as e:
                                logger.error(f"Erreur suppression image: {e}")
                    
                    filename = save_image(file)
                    if filename:
                        recipe.image_filename = filename
            
            # Nettoyage
            Ingredient.query.filter_by(recipe_id=recipe.id).delete()
            Step.query.filter_by(recipe_id=recipe.id).delete()
            
            # Ajout des nouveaux ingrédients
            ingredient_names = request.form.getlist('ingredient_name[]')
            ingredient_quantities = request.form.getlist('ingredient_quantity[]')
            ingredient_units = request.form.getlist('ingredient_unit[]')
            
            for i, name in enumerate(ingredient_names):
                if name.strip():
                    # ✅ CORRIGÉ : Gestion sécurisée avec vérification d'index
                    qty = None
                    if i < len(ingredient_quantities):
                        qty_val = ingredient_quantities[i]
                        if qty_val and qty_val.strip():
                            try:
                                qty = float(qty_val)
                            except ValueError:
                                qty = None
                    
                    unit = ingredient_units[i] if i < len(ingredient_units) else 'g'
                    
                    ingredient = Ingredient(
                        recipe_id=recipe.id,
                        name=name.strip(),
                        quantity=qty,
                        unit=unit
                    )
                    db.session.add(ingredient)
            
            # Ajout des nouvelles étapes
            step_instructions = request.form.getlist('step_instruction[]')
            step_durations = request.form.getlist('step_duration[]')
            
            for i, instruction in enumerate(step_instructions):
                if instruction.strip():
                    # ✅ CORRIGÉ : Gestion sécurisée avec vérification d'index
                    dur = None
                    if i < len(step_durations):
                        dur_val = step_durations[i]
                        if dur_val and dur_val.strip():
                            try:
                                dur = int(dur_val)
                            except ValueError:
                                dur = None
                    
                    step = Step(
                        recipe_id=recipe.id,
                        order=i + 1,
                        instruction=instruction.strip(),
                        duration=dur
                    )
                    db.session.add(step)
            
            db.session.commit()
            flash('Recette modifiée avec succès! ✨', 'success')
            return redirect(url_for('main.recipe_detail', id=recipe.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur modification recette: {e}")
            flash(f'Erreur lors de la sauvegarde : {str(e)}', 'danger')
            return render_template('recipe_form.html', form=form, recipe=recipe, categories=categories)
    
    return render_template('recipe_form.html', form=form, recipe=recipe, categories=categories)


@main.route('/recipe/<int:id>/delete', methods=['POST'])
def recipe_delete(id):
    """Supprimer une recette"""
    recipe = Recipe.query.get_or_404(id)
    
    # ✅ CORRIGÉ : Suppression d'image avec gestion d'erreur
    if recipe.image_filename:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recipe.image_filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Erreur suppression image lors de la suppression de recette: {e}")
    
    db.session.delete(recipe)
    db.session.commit()
    
    flash('Recette supprimée avec succès!', 'success')
    return redirect(url_for('main.index'))


# API endpoints pour les fonctionnalités AJAX
@main.route('/api/recipes')
def api_recipes():
    """API pour récupérer les recettes en JSON"""
    recipes = Recipe.query.all()
    return jsonify([recipe.to_dict() for recipe in recipes])


@main.route('/api/recipe/<int:id>')
def api_recipe(id):
    """API pour récupérer une recette en JSON"""
    recipe = Recipe.query.get_or_404(id)
    return jsonify(recipe.to_dict())


@main.route('/admin/export')
def export_data():
    """Exporte toutes les recettes en JSON"""
    recipes = Recipe.query.all()
    data = [r.to_dict() for r in recipes]
    
    response = jsonify(data)
    response.headers.set('Content-Disposition', 'attachment', filename=f'recipes_backup_{datetime.now().strftime("%Y%m%d")}.json')
    return response


@main.route('/admin/import', methods=['POST'])
def import_data():
    """Importe des recettes depuis un JSON"""
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('main.index'))
        
    file = request.files['file']
    try:
        data = json.load(file)
        
        # ✅ AJOUTÉ : Validation de la structure JSON
        if not isinstance(data, list):
            flash('Format JSON invalide : doit être une liste de recettes', 'danger')
            return redirect(url_for('main.index'))
        
        count = 0
        
        for item in data:
            # ✅ AJOUTÉ : Validation des champs requis
            if not isinstance(item, dict) or 'title' not in item:
                logger.warning(f"Recette ignorée : structure invalide")
                continue
            
            # Vérifier si la recette existe déjà
            exists = Recipe.query.filter_by(title=item['title']).first()
            if not exists:
                # Création de la recette avec valeurs par défaut sécurisées
                recipe = Recipe(
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
                
                # Ajout Ingrédients
                for ing_data in item.get('ingredients', []):
                    if isinstance(ing_data, dict) and 'name' in ing_data:
                        ing = Ingredient(
                            recipe_id=recipe.id,
                            name=ing_data['name'],
                            quantity=ing_data.get('quantity'),
                            unit=ing_data.get('unit', 'g')
                        )
                        db.session.add(ing)
                
                # Ajout Étapes
                for step_data in item.get('steps', []):
                    if isinstance(step_data, dict) and 'instruction' in step_data:
                        step = Step(
                            recipe_id=recipe.id,
                            order=step_data.get('order', 1),
                            instruction=step_data['instruction'],
                            duration=step_data.get('duration')
                        )
                        db.session.add(step)
                
                count += 1
        
        db.session.commit()
        flash(f'{count} nouvelles recettes importées avec succès !', 'success')
        
    except json.JSONDecodeError:
        flash('Fichier JSON invalide', 'danger')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import: {e}")
        flash(f'Erreur lors de l\'import : {str(e)}', 'danger')
        
    return redirect(url_for('main.index'))


@main.route('/settings/category/add', methods=['POST'])
@login_required
def add_category():
    """Ajouter une catégorie"""
    name = request.form.get('category_name')
    if name and name.strip():
        name = name.strip()
        # ✅ AMÉLIORÉ : Validation de la longueur
        if len(name) > 100:
            return jsonify({'success': False, 'message': 'Nom trop long (max 100 caractères).'})
        
        # Vérifier si elle existe déjà
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
                return jsonify({'success': False, 'message': 'Erreur lors de l\'ajout.'})
        else:
            return jsonify({'success': False, 'message': 'Cette famille existe déjà.'})
    return jsonify({'success': False, 'message': 'Nom de catégorie manquant.'})


@main.route('/settings/category/delete/<int:id>', methods=['POST'])
def delete_category(id):
    """Supprimer une catégorie"""
    cat = Category.query.get_or_404(id)
    cat_name = cat.name
    
    # ✅ AJOUTÉ : Gestion des recettes orphelines
    orphan_recipes = Recipe.query.filter_by(category=cat_name).all()
    for recipe in orphan_recipes:
        recipe.category = 'Autre'  # Catégorie par défaut
    
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


@main.route('/init-categories')
@login_required
def init_categories():
    """Initialisation des catégories par défaut POUR L'UTILISATEUR CONNECTÉ"""
    # On ne fait pas db.create_all() ici, c'est risqué en prod, la base doit déjà être prête
    
    defaults = ['Pâtisserie', 'Viennoiserie', 'Confiserie', 'Dessert Glacé', 'Gâteau', 'Tarte', 'Boisson', 'Autre']
    count = 0
    
    for name in defaults:
        # On vérifie si L'UTILISATEUR a déjà cette catégorie
        if not Category.query.filter_by(name=name, user_id=current_user.id).first():
            # On la crée pour LUI
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


@main.route('/settings/category/edit/<int:id>', methods=['POST'])
def edit_category(id):
    """Modifier une catégorie"""
    cat = Category.query.get_or_404(id)
    new_name = request.form.get('new_name')
    
    if new_name and new_name.strip() and new_name.strip() != cat.name:
        new_name = new_name.strip()
        
        # ✅ AMÉLIORÉ : Validation de la longueur
        if len(new_name) > 100:
            return jsonify({'success': False, 'message': 'Nom trop long (max 100 caractères).'})
        
        # Vérifier si le nouveau nom existe déjà
        if Category.query.filter_by(name=new_name).first():
            return jsonify({'success': False, 'message': 'Ce nom de famille existe déjà.'})
        
        try:
            old_name = cat.name
            cat.name = new_name
            
            # Mettre à jour TOUTES les recettes
            recipes_to_update = Recipe.query.filter_by(category=old_name).all()
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


@main.route('/all-recipes')
@login_required
def all_recipes():
    """Page listant toutes les recettes dans un tableau triable"""
    recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.category, Recipe.title).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    # Préparer les données pour le tableau
    recipe_data = []
    for recipe in recipes:
        total_time = (recipe.prep_time or 0) + (recipe.cook_time or 0)
        
        # Récupérer les ingrédients
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
            'difficulty': recipe.difficulty or 'Moyen'
        })
    
    return render_template('all_recipes.html', 
                         recipe_data=recipe_data, 
                         categories=categories)

@main.context_processor
def inject_categories():
    """
    Injecte les catégories de l'utilisateur connecté dans tous les templates.
    Utilisé pour le menu déroulant et la modale de gestion.
    """
    def get_all_categories():
        try:
            # 🔒 SÉCURITÉ : On ne charge que si l'utilisateur est connecté
            if current_user.is_authenticated:
                # On filtre UNIQUEMENT les catégories de l'utilisateur courant
                return Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
            return []
        except Exception as e:
            # On log l'erreur mais on ne fait pas planter le site
            logger.error(f"Erreur context processor: {e}")
            return []
            
    return dict(get_all_categories=get_all_categories)