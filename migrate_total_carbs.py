"""
Script de migration pour passer des glucides par ingrédient 
aux glucides totaux par recette.

Ce script :
1. Ajoute la colonne total_carbs à la table recipes
2. Calcule et migre les glucides existants
3. Optionnellement, nettoie la colonne carbs de la table ingredients

IMPORTANT : Faites une sauvegarde de votre base de données avant d'exécuter ce script !
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Recipe, Ingredient
from sqlalchemy import inspect, text

# Créer l'instance de l'application
app = create_app()


def migration_add_total_carbs():
    """Migration pour ajouter total_carbs aux recettes"""
    
    print("🔄 Démarrage de la migration...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Étape 1 : Vérifier si la colonne total_carbs existe déjà
        columns = [col['name'] for col in inspector.get_columns('recipes')]
        
        if 'total_carbs' not in columns:
            print("➕ Ajout de la colonne 'total_carbs' à la table recipes...")
            try:
                with db.engine.connect() as conn:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN total_carbs FLOAT DEFAULT 0"))
                    conn.commit()
                print("✅ Colonne 'total_carbs' ajoutée")
            except Exception as e:
                print(f"❌ Erreur lors de l'ajout de la colonne : {e}")
                return False
        else:
            print("ℹ️  La colonne 'total_carbs' existe déjà")
        
        # Étape 2 : Migrer les données existantes
        print("\n📊 Migration des données existantes...")
        recipes = Recipe.query.all()
        
        if not recipes:
            print("ℹ️  Aucune recette à migrer")
            return True
        
        migrated_count = 0
        for recipe in recipes:
            try:
                # Calculer le total des glucides à partir des ingrédients
                total = 0
                for ing in recipe.ingredients:
                    if hasattr(ing, 'carbs') and ing.carbs:
                        total += ing.carbs
                
                recipe.total_carbs = total
                print(f"   • {recipe.title}: {total:.1f}g de glucides")
                migrated_count += 1
            except Exception as e:
                print(f"   ⚠️  Erreur pour {recipe.title}: {e}")
        
        try:
            db.session.commit()
            print(f"✅ {migrated_count} recettes migrées sur {len(recipes)}")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {e}")
            db.session.rollback()
            return False
        
        # Étape 3 : Information sur la colonne carbs
        print("\n📋 Information sur la colonne 'carbs' dans ingredients...")
        
        ingredient_columns = [col['name'] for col in inspector.get_columns('ingredients')]
        
        if 'carbs' in ingredient_columns:
            print("ℹ️  La colonne 'carbs' existe toujours dans la table ingredients")
            print("   Elle ne sera plus utilisée par l'application mais reste présente")
            print("   (SQLite ne supporte pas DROP COLUMN nativement)")
            print("\n💡 Pour la supprimer complètement, utilisez l'option 2 du menu")
        else:
            print("✅ La colonne 'carbs' n'existe plus")
        
        print("\n✨ Migration terminée avec succès!")
        print("\nRésumé :")
        print(f"   • {migrated_count} recettes mises à jour")
        print("   • Les glucides sont maintenant stockés au niveau de la recette")
        print("   • Les nouveaux formulaires n'afficheront plus les champs glucides par ingrédient")
        
        return True


def migration_cleanup_ingredients_table():
    """
    Migration optionnelle pour nettoyer complètement la table ingredients
    ATTENTION : Opération destructive !
    """
    print("\n🧹 Nettoyage complet de la table ingredients...")
    print("⚠️  ATTENTION : Cette opération va recréer la table ingredients !")
    print("⚠️  Toutes les données seront préservées, mais la structure changera")
    print("⚠️  La colonne 'carbs' sera définitivement supprimée")
    
    response = input("\nVoulez-vous continuer ? (tapez 'OUI' en majuscules) : ")
    
    if response != 'OUI':
        print("❌ Nettoyage annulé")
        return False
    
    with app.app_context():
        try:
            # Récupérer toutes les données
            print("📦 Sauvegarde des données existantes...")
            all_ingredients = []
            for ing in Ingredient.query.all():
                all_ingredients.append({
                    'recipe_id': ing.recipe_id,
                    'name': ing.name,
                    'quantity': ing.quantity,
                    'unit': ing.unit
                })
            
            print(f"   • {len(all_ingredients)} ingrédients sauvegardés")
            
            # Supprimer et recréer la table
            print("🔨 Recréation de la table...")
            db.session.execute(text("DROP TABLE IF EXISTS ingredients"))
            db.session.execute(text("""
                CREATE TABLE ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    quantity FLOAT,
                    unit VARCHAR(50),
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
                )
            """))
            
            # Réinsérer les données
            print("📥 Restauration des données...")
            for ing_data in all_ingredients:
                db.session.execute(
                    text("""
                        INSERT INTO ingredients (recipe_id, name, quantity, unit)
                        VALUES (:recipe_id, :name, :quantity, :unit)
                    """),
                    ing_data
                )
            
            db.session.commit()
            print(f"✅ Table ingredients nettoyée ({len(all_ingredients)} ingrédients restaurés)")
            print("✅ La colonne 'carbs' a été définitivement supprimée")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage : {e}")
            db.session.rollback()
            print("🔄 Rollback effectué - aucune modification n'a été appliquée")
            return False


def verify_migration():
    """Vérifier que la migration s'est bien passée"""
    print("\n🔍 Vérification de la migration...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Vérifier la structure
        recipe_columns = [col['name'] for col in inspector.get_columns('recipes')]
        ingredient_columns = [col['name'] for col in inspector.get_columns('ingredients')]
        
        print("\n📋 Structure de la table 'recipes' :")
        print(f"   • Colonnes : {', '.join(recipe_columns)}")
        has_total_carbs = 'total_carbs' in recipe_columns
        print(f"   • total_carbs présent : {'✅' if has_total_carbs else '❌'}")
        
        print("\n📋 Structure de la table 'ingredients' :")
        print(f"   • Colonnes : {', '.join(ingredient_columns)}")
        has_carbs = 'carbs' in ingredient_columns
        print(f"   • carbs présent : {'⚠️ Oui (inutilisé)' if has_carbs else '✅ Non'}")
        
        # Vérifier quelques recettes
        recipes = Recipe.query.limit(5).all()
        print(f"\n📊 Aperçu de {len(recipes)} recettes :")
        for recipe in recipes:
            carbs_value = recipe.total_carbs if hasattr(recipe, 'total_carbs') else 0
            print(f"   • {recipe.title}: {carbs_value:.1f}g")
        
        # Résumé
        print("\n" + "=" * 70)
        print("RÉSUMÉ DE LA VÉRIFICATION")
        print("=" * 70)
        
        if has_total_carbs and not has_carbs:
            print("✅ Migration complète : total_carbs ajouté, carbs supprimé")
        elif has_total_carbs and has_carbs:
            print("⚠️  Migration partielle : total_carbs ajouté, carbs toujours présent")
            print("   → Utilisez l'option 2 pour supprimer la colonne carbs")
        else:
            print("❌ Migration non effectuée : total_carbs absent")
        
        print("=" * 70)


if __name__ == '__main__':
    print("=" * 70)
    print(" " * 15 + "MIGRATION : Glucides par recette")
    print("=" * 70)
    print("\n⚠️  IMPORTANT : Sauvegardez votre base de données avant de continuer !")
    print("   Exemple : copy instance\\recipes.db instance\\recipes.db.backup\n")
    
    # Menu principal
    while True:
        print("\n" + "=" * 70)
        print("Que souhaitez-vous faire ?")
        print("=" * 70)
        print("1. Lancer la migration (ajouter total_carbs et migrer les données)")
        print("2. Nettoyer la table ingredients (supprimer la colonne carbs)")
        print("3. Vérifier la migration")
        print("4. Quitter")
        print("=" * 70)
        
        choice = input("\nVotre choix (1-4) : ").strip()
        
        if choice == '1':
            response = input("\n⚠️  Avez-vous fait une sauvegarde de votre base de données ? (oui/non) : ")
            if response.lower() == 'oui':
                success = migration_add_total_carbs()
                if success:
                    print("\n✅ Vous pouvez maintenant utiliser les nouveaux fichiers !")
                    print("   • models.py")
                    print("   • routes.py")
                    print("   • recipe_form.html")
                    print("   • recipe_detail.html")
            else:
                print("❌ Veuillez d'abord faire une sauvegarde de votre base de données !")
                print("   Commande : copy instance\\recipes.db instance\\recipes.db.backup")
        
        elif choice == '2':
            migration_cleanup_ingredients_table()
        
        elif choice == '3':
            verify_migration()
        
        elif choice == '4':
            print("\n👋 Au revoir !")
            break
        
        else:
            print("❌ Choix invalide, veuillez réessayer")