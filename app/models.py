from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer
import uuid

# Table d'association Recettes <-> Tags
recipe_tags = db.Table('recipe_tags',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipes.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    # Relations
    recipes = db.relationship('Recipe', backref='author', lazy='dynamic')
    categories = db.relationship('Category', backref='author', lazy='dynamic')
    # 🆕 Historique
    history = db.relationship('CookingHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    tips = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    prep_time = db.Column(db.Integer)
    cook_time = db.Column(db.Integer)
    servings = db.Column(db.Integer, default=4)
    difficulty = db.Column(db.String(50))
    category = db.Column(db.String(100))
    total_carbs = db.Column(db.Float, default=0)
    rating = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(500), nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    share_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    ingredients = db.relationship('Ingredient', backref='recipe', lazy='dynamic', cascade='all, delete-orphan')
    steps = db.relationship('Step', backref='recipe', lazy='dynamic', cascade='all, delete-orphan', order_by='Step.order')
    # 🆕 Tags
    tags = db.relationship('Tag', secondary=recipe_tags, lazy='subquery', backref=db.backref('recipes', lazy=True))
    # 🆕 Historique lié à cette recette
    history_entries = db.relationship('CookingHistory', backref='recipe', lazy='dynamic')
    
    @property
    def carbs_per_serving(self):
        if self.servings and self.servings > 0:
            return self.total_carbs / self.servings
        return 0
     
    def generate_share_token(self):
        self.share_token = uuid.uuid4().hex
        return self.share_token

    def revoke_share_token(self):
        self.share_token = None
    
    @property
    def total_time(self):
        return (self.prep_time or 0) + (self.cook_time or 0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'tips': self.tips,
            'image_filename': self.image_filename,
            'prep_time': self.prep_time,
            'cook_time': self.cook_time,
            'servings': self.servings,
            'difficulty': self.difficulty,
            'category': self.category,
            'total_carbs': self.total_carbs,
            'rating': self.rating,
            'source': self.source,
            'is_favorite': self.is_favorite,
            'carbs_per_serving': self.carbs_per_serving,
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            'steps': [step.to_dict() for step in self.steps.order_by(Step.order)],
            'tags': [tag.name for tag in self.tags] # 🆕
        }

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(50))
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'quantity': self.quantity, 'unit': self.unit}

class Step(db.Model):
    __tablename__ = 'steps'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    instruction = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer)
    
    def to_dict(self):
        return {'id': self.id, 'order': self.order, 'instruction': self.instruction, 'duration': self.duration}

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name}

# 🆕 MODÈLE TAGS
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # ✅ Isolation
    name = db.Column(db.String(50), nullable=False)
    
    def __repr__(self):
        return self.name

# 🆕 MODÈLE HISTORIQUE
class CookingHistory(db.Model):
    __tablename__ = 'cooking_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    cooked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recipe_title': self.recipe.title,
            'recipe_id': self.recipe.id,
            'date': self.cooked_at.strftime('%Y-%m-%d %H:%M')
        }