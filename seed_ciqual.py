import csv
import os
from app import create_app, db
from app.models import CiqualFood

app = create_app()

GLUCIDES_KEY = 'Glucides\n(g\n100 g)'

def parse_carbs(raw):
    """Convertit une valeur CIQUAL en float, ou 0.0 si non mesurable/inconnue."""
    val = (raw or '').strip()
    if not val or val == '-':
        return 0.0
    if val.lower() == 'traces':
        return 0.05
    if val.startswith('<'):
        val = val.replace('<', '').strip()
    val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0.0


def seed_database():
    with app.app_context():
        # Vide la table pour forcer un réimport propre (au lieu de bloquer si déjà pleine)
        CiqualFood.query.delete()
        db.session.commit()

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
                    print("❌ Aucune colonne détectée !")
                    return

                if GLUCIDES_KEY not in reader.fieldnames:
                    print(f"❌ Colonne '{GLUCIDES_KEY!r}' introuvable. Colonnes réelles : {reader.fieldnames}")
                    return

                print(f"✅ Colonne Glucides trouvée : {GLUCIDES_KEY!r}")

                foods = []
                skipped = 0

                for row in reader:
                    try:
                        # Garde la casse d'origine (utile pour affichage), le matching
                        # se fera insensible à la casse côté requête SQL
                        name = row.get('alim_nom_fr', '').strip()
                        if not name:
                            skipped += 1
                            continue

                        carbs = parse_carbs(row.get(GLUCIDES_KEY, ''))
                        foods.append(CiqualFood(name=name, carbs_per_100g=carbs))
                    except Exception:
                        skipped += 1
                        continue

                if foods:
                    db.session.bulk_save_objects(foods)
                    db.session.commit()
                    print(f"✅ Succès ! {len(foods)} aliments ajoutés.")
                    print(f"⚠️  {skipped} lignes ignorées.")
                else:
                    print("❌ Aucun aliment n'a pu être ajouté.")

        except UnicodeDecodeError:
            print("❌ Erreur d'encodage ! Essayez avec 'utf-8-sig' ou 'cp1252'.")
        except Exception as e:
            print(f"❌ Erreur inattendue : {e}")


if __name__ == "__main__":
    seed_database()