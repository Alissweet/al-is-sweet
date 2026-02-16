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
    
    # Enregistrement des blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    from app.auth import auth
    app.register_blueprint(auth)

    # ✅ SUPPRIMÉ : inject_categories retiré d'ici
    # Il est géré de façon sécurisée dans routes.py (filtré par user)

    # ✅ AJOUTÉ : Création des tables pour Neon au démarrage
    with app.app_context():
        db.create_all()

    # ✅ DÉPLACÉ : user_loader à l'intérieur de la factory
    from app import models

    @login.user_loader
    def load_user(id):
        return models.User.query.get(int(id))
    
    @app.context_processor
    def inject_categories():
        def get_all_categories():
            try:
                from flask_login import current_user
                from app.models import Category
                if current_user.is_authenticated:
                    return Category.query.filter_by(
                        user_id=current_user.id).order_by(Category.name).all()
                return []  # ✅ Retourne liste vide si non connecté (page login etc.)
            except Exception as e:
                logger.error(f"Erreur context processor: {e}")
                return []
        return dict(get_all_categories=get_all_categories)
        
    return app