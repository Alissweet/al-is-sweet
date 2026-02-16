from app import create_app, db
import time

app = create_app()

if __name__ == '__main__':
    # Attendre que la base de données soit prête
    with app.app_context():
        # Créer les tables
        db.create_all()
        print("✅ Base de données initialisée!")
    
    # Lancer l'application
    app.run(debug=True, host='0.0.0.0', port=5000)