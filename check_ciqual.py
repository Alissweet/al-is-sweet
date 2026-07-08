from app import create_app
from app.models import CiqualFood

app = create_app()

with app.app_context():
    noms_a_verifier = ["Ail, cru", "Poivron rouge, cru", "Fromage type feta, au lait de vache 100%"]

    for nom in noms_a_verifier:
        food = CiqualFood.query.filter_by(name=nom).first()
        if food:
            print(f"✅ {food.name} -> {food.carbs_per_100g} g glucides / 100g")
        else:
            print(f"❌ Aucun aliment trouvé pour le nom exact : {nom!r}")

    total = CiqualFood.query.count()
    print(f"\nTotal en base : {total} aliments")