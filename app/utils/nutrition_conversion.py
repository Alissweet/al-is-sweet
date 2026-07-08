"""
Conversion déterministe unité -> grammes.

Sources : USDA FoodData Central (densités), NIST Handbook 44
(1 tbsp = 14.7868 mL, 1 tsp = 4.9289 mL), recoupé avec King Arthur
Baking Ingredient Weight Chart.

⚠️ Moyennes culinaires standards US. Ne remplacent pas une pesée réelle.
Pour un usage médical (dosage d'insuline), une balance de cuisine reste
la référence la plus fiable. Tout ingrédient absent de cette table DOIT
être saisi manuellement en grammes : ne jamais deviner.
"""

UNIT_TO_GRAMS_UNIVERSAL = {
    'g': 1.0,
    'kg': 1000.0,
    'ml': 1.0,
    'l': 1000.0,
}

INGREDIENT_WEIGHTS = {
    'farine': {'c.à.s': 7.5, 'tablespoon': 7.5, 'c.à.c': 2.5, 'teaspoon': 2.5,
               'tasse': 125.0, 'cup': 125.0},
    'sucre': {'c.à.s': 12.38, 'tablespoon': 12.38, 'c.à.c': 4.13, 'teaspoon': 4.13,
              'tasse': 200.0, 'cup': 200.0},
    'sucre glace': {'c.à.s': 7.06, 'tablespoon': 7.06, 'c.à.c': 2.35, 'teaspoon': 2.35,
                    'tasse': 113.0, 'cup': 113.0},
    'cassonade': {'c.à.s': 13.31, 'tablespoon': 13.31, 'c.à.c': 4.44, 'teaspoon': 4.44,
                  'tasse': 213.0, 'cup': 213.0},
    'beurre': {'c.à.s': 14.13, 'tablespoon': 14.13, 'c.à.c': 4.71, 'teaspoon': 4.71,
               'tasse': 226.0, 'cup': 226.0},
    'lait': {'c.à.s': 15.0, 'tablespoon': 15.0, 'c.à.c': 5.0, 'teaspoon': 5.0,
             'tasse': 240.0, 'cup': 240.0},
    'miel': {'c.à.s': 21.0, 'tablespoon': 21.0, 'c.à.c': 7.0, 'teaspoon': 7.0,
             'tasse': 340.0, 'cup': 340.0},
    'huile': {'c.à.s': 13.5, 'tablespoon': 13.5, 'c.à.c': 4.5, 'teaspoon': 4.5,
              'tasse': 218.0, 'cup': 218.0},
    'cacao': {'c.à.s': 5.25, 'tablespoon': 5.25, 'c.à.c': 1.75, 'teaspoon': 1.75,
              'tasse': 84.0, 'cup': 84.0},
    'sel': {'c.à.s': 18.0, 'tablespoon': 18.0, 'c.à.c': 6.0, 'teaspoon': 6.0},
    'levure': {'c.à.s': 9.0, 'tablespoon': 9.0, 'c.à.c': 3.0, 'teaspoon': 3.0,
               'sachet': 7.0},
    'crème': {'c.à.s': 20.0, 'tablespoon': 15.0, 'c.à.c': 5.0, 'teaspoon': 5.0,
              'tasse': 240.0, 'cup': 240.0},
    'yaourt': {'c.à.s': 20.0, 'tablespoon': 15.0, 'c.à.c': 5.0, 'teaspoon': 5.0,
               'tasse': 245.0, 'cup': 245.0},
}

UNIT_ALIASES = {
    'c.à.s': 'c.à.s', 'tablespoon': 'tablespoon',
    'c.à.c': 'c.à.c', 'teaspoon': 'teaspoon',
    'tasse': 'tasse', 'cup': 'cup',
    'sachet': 'sachet', 'pincée': 'pincée',
}

PINCEE_GRAMS = 0.36  # approximation grossière, pas de source officielle


def convert_to_grams(ingredient_name: str, qty: float, unit: str):
    """Retourne le poids en grammes, ou None si non convertible fiablement."""
    unit_norm = (unit or '').strip().lower()
    name_norm = (ingredient_name or '').strip().lower()

    if unit_norm in UNIT_TO_GRAMS_UNIVERSAL:
        return qty * UNIT_TO_GRAMS_UNIVERSAL[unit_norm]

    if unit_norm == 'pincée':
        return qty * PINCEE_GRAMS

    if unit_norm in UNIT_ALIASES:
        for keyword, weights in INGREDIENT_WEIGHTS.items():
            if keyword in name_norm and unit_norm in weights:
                return qty * weights[unit_norm]
        return None

    return None