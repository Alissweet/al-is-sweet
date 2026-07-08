import re
from sqlalchemy import func
from app.models import CiqualFood

# Mots signalant un produit transformé/composé — pénalisés fortement
# sauf si l'ingrédient de la recette les mentionne explicitement
EXCLUDED_KEYWORDS = ['préemballé', 'tartinade', 'sauce', 'plat cuisiné',
                     'conserve', 'surgelé', 'pané', 'nappage', 'chips',
                     'glace', 'gâteau', 'cake', 'biscuit', 'tzatziki']


def singularize_fr(word):
    if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def normalize_words(text):
    words = re.findall(r"[a-zàâäéèêëïîôöùûüç']+", text.lower())
    return [singularize_fr(w) for w in words if len(w) > 2]


def words_match(search_word, food_word):
    """Compare par préfixe (min 4 lettres communes) pour absorber les variantes
    grammaticales : grec/grecque, poivron/poivrons, etc."""
    if search_word == food_word:
        return True
    min_len = min(len(search_word), len(food_word))
    if min_len < 4:
        return False
    prefix_len = min(min_len, 5)
    return search_word[:prefix_len] == food_word[:prefix_len]


def find_best_ciqual_match(ingredient_name):
    name_clean = ingredient_name.strip()

    exact = CiqualFood.query.filter(
        func.lower(CiqualFood.name) == name_clean.lower()
    ).first()
    if exact:
        return exact

    search_words = normalize_words(name_clean)
    if not search_words:
        return None

    candidates = CiqualFood.query.filter(
        CiqualFood.name.ilike(f"%{search_words[0]}%")
    ).all()

    if not candidates:
        return None

    def score(food):
        food_words = normalize_words(food.name)
        matched = sum(
            1 for sw in search_words
            if any(words_match(sw, fw) for fw in food_words)
        )
        match_ratio = matched / len(search_words)
        is_transformed = any(kw in food.name.lower() for kw in EXCLUDED_KEYWORDS)
        transform_penalty = -10 if is_transformed else 0
        return (round(match_ratio, 3), transform_penalty, -len(food.name))

    best = max(candidates, key=score)
    if score(best)[0] > 0:
        return best
    return None