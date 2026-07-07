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

        # Chemin du fichier
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'app', 'static', 'data', 'ciqual.csv')
        
        print(f"Lecture du fichier : {csv_path}")
        
        if not os.path.exists(csv_path):
            print(f"❌ Fichier introuvable ! Vérifiez le chemin : {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                if not reader.fieldnames:
                    print("❌ Aucune colonne détectée ! Le fichier est vide ou mal formaté.")
                    return
                
                print(f"✅ Colonnes détectées : {reader.fieldnames}")
                print(f"   Nombre total de colonnes : {len(reader.fieldnames)}")
                
                foods = []
                skipped = 0
                
                for row in reader:
                    try:
                        name = row.get('alim_nom_fr', '').strip().lower()
                        if not name:
                            skipped += 1
                            continue
                        
                        # La colonne s'appelle 'Glucides (g 100 g)' dans le fichier
                        carbs_str = row.get('Glucides (g 100 g)', '0')
                        carbs_str = carbs_str.replace(',', '.')
                        
                        if '<' in carbs_str or 'traces' in carbs_str.lower():
                            carbs = 0.0
                        else:
                            try:
                                carbs = float(carbs_str)
                            except ValueError:
                                carbs = 0.0
                        
                        foods.append(CiqualFood(name=name, carbs_per_100g=carbs))
                    except Exception:
                        skipped += 1
                        continue
                
                if foods:
                    db.session.bulk_save_objects(foods)
                    db.session.commit()
                    print(f"✅ Succès ! {len(foods)} aliments ajoutés.")
                    print(f"⚠️  {skipped} lignes ignorées (nom vide ou erreur).")
                else:
                    print("❌ Aucun aliment n'a pu être ajouté.")
                    
        except UnicodeDecodeError:
            print("❌ Erreur d'encodage ! Essayez avec 'utf-8-sig' ou 'cp1252'.")
        except Exception as e:
            print(f"❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    seed_database()