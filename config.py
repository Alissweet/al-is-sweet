import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ✅ Clé secrète robuste sans fallback lisible
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY non définie dans les variables d'environnement")

    # ✅ Correction postgres:// → postgresql:// pour Neon + SQLAlchemy
    _db_url = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:sweetpassword123@localhost:5433/al_is_sweet'
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ✅ Neon : SSL + gestion du cold start (instance gratuite)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"sslmode": "require"},
        "pool_pre_ping": True,
        "pool_recycle": 300,
}

    # --- IMAGES (Hybride Cloud/Local) ---
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # --- EMAIL ---
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')