import csv
import os
from app import create_app, db
from app.models import CiqualFood

app = create_app()

def diagnostic():
    with app.app_context():
        # Chemin du fichier
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'app', 'static', 'data', 'ciqual.csv')
        
        print(f"🔍 1. Recherche du fichier : {csv_path}")
        if not os.path.exists(csv_path):
            print(f"❌ Fichier introuvable !")
            return
        else:
            print(f"✅ Fichier trouvé !")
            print(f"   Taille : {os.path.getsize(csv_path)} octets")
        
        # 2. Lire les premières lignes brutes
        print("\n🔍 2. Aperçu des 5 premières lignes brutes :")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            for i in range(5):
                line = f.readline()
                if not line:
                    break
                print(f"   Ligne {i+1} : {line.strip()}")
        
        # 3. Lire avec csv.DictReader
        print("\n🔍 3. Test avec csv.DictReader :")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            if reader.fieldnames is None:
                print("❌ Aucune colonne détectée ! Le fichier est vide ou mal formaté.")
                return
                
            print(f"✅ Colonnes détectées : {reader.fieldnames}")
            print(f"   Nombre de colonnes : {len(reader.fieldnames)}")
            
            # 4. Afficher les 3 premières lignes parsées
            print("\n🔍 4. Aperçu des 3 premières lignes parsées :")
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                print(f"   Ligne {i+1} : {row}")
            
            # 5. Compter le nombre total de lignes
            f.seek(0)
            reader = csv.DictReader(f, delimiter=';')
            total_rows = sum(1 for _ in reader)
            print(f"\n🔍 5. Nombre total de lignes dans le fichier : {total_rows}")
            
            # 6. Vérifier les colonnes "alim_nom_fr" et "Glucides"
            f.seek(0)
            reader = csv.DictReader(f, delimiter=';')
            first_row = next(reader, None)
            if first_row:
                print("\n🔍 6. Vérification des colonnes clés sur la première ligne :")
                print(f"   'alim_nom_fr' existe ? {'OUI' if 'alim_nom_fr' in first_row else 'NON'}")
                print(f"   Valeur de 'alim_nom_fr' : {first_row.get('alim_nom_fr', '')}")
                print(f"   'Glucides (g/100 g)' existe ? {'OUI' if 'Glucides (g/100 g)' in first_row else 'NON'}")
                print(f"   Valeur de 'Glucides (g/100 g)' : {first_row.get('Glucides (g/100 g)', '')}")
                print(f"   Toutes les colonnes : {list(first_row.keys())}")
            else:
                print("❌ Impossible de lire la première ligne.")

if __name__ == "__main__":
    diagnostic()