from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
import os
import logging

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
login.login_view = 'auth.login'
login.login_message = 'Veuillez vous connecter pour accéder à cette page.'

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Blueprints ────────────────────────────────────────────
    from app.blueprints.recipes.routes import recipes_bp
    app.register_blueprint(recipes_bp)

    from app.blueprints.tools.routes import tools_bp
    app.register_blueprint(tools_bp)

    from app.blueprints.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from app.auth import auth
    app.register_blueprint(auth)

    # ── User loader ───────────────────────────────────────────
    from app import models

    @login.user_loader
    def load_user(id):
        return db.session.get(models.User, int(id))

    # ── Context processor ─────────────────────────────────────
    @app.context_processor
    def inject_categories():
        def get_all_categories():
            try:
                from flask_login import current_user
                from app.models import Category
                if current_user.is_authenticated:
                    return Category.query.filter_by(
                        user_id=current_user.id).order_by(Category.name).all()
                return []
            except Exception as e:
                logger.error(f"Erreur context processor: {e}")
                return []
        return dict(get_all_categories=get_all_categories)

    # ── Pages d'erreur ────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('errors/500.html'), 500

    with app.app_context():
        db.create_all()

    return app
