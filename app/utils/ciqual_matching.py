import re
from sqlalchemy import func
from app.models import CiqualFood

EXCLUDED_KEYWORDS = ['préemballé', 'tartinade', 'sauce', 'plat cuisiné',
                     'conserve', 'surgelé', 'pané', 'nappage', 'chips']


def singularize_fr(word):
    if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def normalize_words(text):
    words = re.findall(r"[a-zàâäéèêëïîôöùûüç']+", text.lower())
    return [singularize_fr(w) for w in words if len(w) > 2]


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

    def score(food):
        food_words = normalize_words(food.name)
        matched = sum(1 for w in search_words if w in food_words)
        is_transformed = any(kw in food.name.lower() for kw in EXCLUDED_KEYWORDS)
        return (matched, -len(food.name), 0 if not is_transformed else -100)

    if candidates:
        best = max(candidates, key=score)
        if score(best)[0] > 0:
            return best

    return None