from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, IntegerField, FloatField, 
                     SelectField, FieldList, FormField, Form)
from wtforms.validators import DataRequired, Optional, NumberRange

class IngredientForm(Form):
    name = StringField('Ingrédient', validators=[DataRequired()])
    quantity = FloatField('Quantité', validators=[Optional()])
    unit = SelectField('Unité', choices=[
        ('g', 'grammes'),
        ('kg', 'kilogrammes'),
        ('ml', 'millilitres'),
        ('L', 'litres'),
        ('pièce', 'pièce(s)'),
        ('c.à.s', 'cuillère(s) à soupe'),
        ('c.à.c', 'cuillère(s) à café'),
        ('pincée', 'pincée(s)'),
        ('tasse', 'tasse(s)'),
        ('sachet', 'sachet(s)')
    ])
    # ✅ SUPPRIMÉ : Le champ carbs n'existe plus dans le modèle Ingredient


class StepForm(Form):
    instruction = TextAreaField('Instruction', validators=[DataRequired()])
    duration = IntegerField('Durée (min)', validators=[Optional()])


class RecipeForm(FlaskForm):
    title = StringField('Nom de la recette', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    tips = TextAreaField('Astuces', validators=[Optional()])  # ✅ AJOUTÉ : Manquait dans le formulaire
    image = FileField('Photo du plat', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images uniquement!')
    ])
    prep_time = IntegerField('Temps de préparation (min)', validators=[Optional(), NumberRange(min=0)])
    cook_time = IntegerField('Temps de cuisson (min)', validators=[Optional(), NumberRange(min=0)])
    servings = IntegerField('Nombre de portions', validators=[Optional(), NumberRange(min=1)], default=4)
    difficulty = SelectField('Difficulté', choices=[
        ('Facile', 'Facile'),
        ('Moyen', 'Moyen'),
        ('Difficile', 'Difficile')
    ])
    # ✅ CORRIGÉ : Les catégories doivent être chargées dynamiquement
    # NOTE: Les choices seront définies dans les routes avec form.category.choices = [...]
    category = SelectField('Catégorie', choices=[], validators=[Optional()])
    
    # ✅ AJOUTÉ : Le champ total_carbs qui manquait
    total_carbs = FloatField('Total glucides (g)', validators=[Optional(), NumberRange(min=0)], default=0)


# ✅ FONCTION HELPER pour charger les catégories dynamiquement
def populate_category_choices(form, categories_list):
    """
    Remplit les choix de catégories depuis la base de données
    
    Usage dans les routes:
        form = RecipeForm()
        populate_category_choices(form, categories)
    """
    form.category.choices = [(cat, cat) for cat in categories_list]
    return form