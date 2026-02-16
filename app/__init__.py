from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from flask_mail import Mail
import os
import logging

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
login.login_view = 'auth.login'
login.login_message = 'Veuillez vous connecter pour accéder à cette page.'
mail = Mail()

logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Créer le dossier uploads s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Enregistrement des routes
    from app.routes import main
    app.register_blueprint(main)
    
    # Enregistrement du blueprint Auth
    from app.auth import auth
    app.register_blueprint(auth)
    
    # ✅ AJOUT : Context processor global pour les catégories
    @app.context_processor
    def inject_categories():
        """Rend les catégories disponibles dans tous les templates"""
        from app.models import Category
        def get_all_categories():
            try:
                return Category.query.order_by(Category.name).all()
            except Exception as e:
                logger.error(f"Erreur récupération catégories: {e}")
                return []
        return dict(get_all_categories=get_all_categories)
    
    return app

# Loader utilisateur
from app import models
@login.user_loader
def load_user(id):
    return models.User.query.get(int(id))