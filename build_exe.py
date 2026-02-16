import PyInstaller.__main__
import os
import shutil

# Nom de l'application
APP_NAME = "Al_is_Sweet_App"

# Nettoyage des builds précédents
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Commande PyInstaller
PyInstaller.__main__.run([
    'run.py',                       # Script principal
    '--name=%s' % APP_NAME,         # Nom de l'exe
    '--onefile',                    # Un seul fichier .exe
    '--windowed',                   # Pas de console noire au lancement
    '--icon=app/static/favicon.ico', # (Optionnel) Si tu as une icône
    
    # Inclusion des dossiers de données (Templates, Static, Migrations)
    '--add-data=app/templates;app/templates',
    '--add-data=app/static;app/static',
    '--add-data=migrations;migrations',
    
    # Inclusion du .env (Optionnel, sinon l'utilisateur doit le fournir)
    '--add-data=.env;.',
    
    # Imports cachés souvent manqués par PyInstaller avec Flask-SQLAlchemy
    '--hidden-import=pg8000',
    '--hidden-import=psycopg2',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=flask_migrate',
])

print(f"✅ Compilation terminée ! L'exécutable est dans le dossier 'dist/{APP_NAME}.exe'")