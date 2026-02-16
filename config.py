import os
import sys
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'al-is-sweet-secret-key-2024'
    
    # --- BASE DE DONNÉES ---
    # Si DATABASE_URL est défini (Prod ou .env), on l'utilise.
    # Sinon, on fallback sur la config Docker locale par défaut.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:sweetpassword123@localhost:5433/al_is_sweet'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- GESTION DES IMAGES (Hybride) ---
    # Si une URL Cloudinary est présente, on passe en mode Cloud
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    
    # Configuration locale (Repli)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app/static/uploads')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
     # --- CONFIGURATION EMAIL (Gmail) ---
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    # On récupère ces infos depuis le .env pour la sécurité
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')