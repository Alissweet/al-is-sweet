import csv
import os
from app import create_app, db
from app.models import CiqualFood

app = create_app()

def seed_database():
    with app.app_context():
        if CiqualFood.query.count() > 0:
            print("Base CIQUAL déjà pleine.")
            return

        # Construire le chemin de façon robuste
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'app', 'static', 'data', 'ciqual.csv')
        
        print(f"Lecture du fichier: {csv_path}")
        
        if not os.path.exists(csv_path):
            print(f"❌ Fichier introuvable: {csv_path}")
            print("Vérifiez que le fichier est bien dans app/static/data/ciqual.csv")
            return

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            print(f"Colonnes: {reader.fieldnames}")
            
            # Reste du code identique...
            foods = []
            for row in reader:
                try:
                    name = row.get('alim_nom_fr', '').lower()
                    if not name:
                        continue
                    
                    carbs_str = row.get('Glucides (g/100 g)', '0')
                    carbs_str = carbs_str.replace(',', '.')
                    
                    if '<' in carbs_str or 'traces' in carbs_str.lower():
                        carbs = 0.0
                    else:
                        carbs = float(carbs_str)
                    
                    foods.append(CiqualFood(name=name, carbs_per_100g=carbs))
                except:
                    continue
            
            db.session.bulk_save_objects(foods)
            db.session.commit()
            print(f"Succès ! {len(foods)} aliments ajoutés.")

if __name__ == "__main__":
    seed_database()