"""
Indian staples, looked up before USDA.

WHY THIS EXISTS
USDA is a good database of American food. Asked for "roti" it offers
"Bread, chapati or roti, plain, commercially prepared", which is a packet
product rather than what came off a tawa, and asked for "dal" it returns
whatever branded item happens to share the word. Every macro in the
report comes from the lookup, so a wrong match quietly poisons the whole
day.

So the common Indian foods are held here and USDA is the fallback. The
table is small on purpose: thirty foods people actually log, rather than
an attempt to replace a national database.

ABOUT THE NUMBERS
These are typical published values for home prepared portions, per 100
grams as eaten. They are approximate, because a dal cooked thin and a dal
cooked thick are not the same food, and no table can fix that. The UI
names the source for every row so nobody has to guess where a number came
from.

For anything beyond a demo the right move is the ICMR-NIN Indian Food
Composition Tables 2017 themselves, which is what these values follow.
Note the licence before bundling anyone's packaged copy of them: the
widely used GitHub version moved to AGPL-3.0 in April 2025.
"""

from __future__ import annotations

import re

from .usda import FoodMatch

# A long phrase is usually several foods that were never split apart, and
# matching one word of it would put the whole amount against the wrong
# food. Anything longer than this is handed to USDA instead.
MAX_WORDS_FOR_LOOSE_MATCH = 5

SOURCE = "Indian staples table (typical values, IFCT style)"

# name: (protein, fat, carbohydrate) per 100g as eaten, plus the aliases
# people actually type.
TABLE: dict[str, tuple[tuple[float, float, float], tuple[str, ...]]] = {
    # Breads
    "roti": ((8.1, 4.0, 46.0), ("chapati", "chapathi", "phulka", "rotis")),
    "paratha": ((7.0, 12.0, 45.0), ("parantha", "porotta")),
    "naan": ((8.7, 5.1, 50.0), ()),
    "puri": ((6.9, 17.0, 45.0), ("poori",)),
    # Rice and grains
    "rice": ((2.7, 0.3, 28.0), ("chawal", "steamed rice", "boiled rice", "white rice")),
    "biryani": ((6.0, 7.0, 25.0), ("biriyani", "pulao", "pulav")),
    "khichdi": ((4.0, 3.0, 20.0), ("khichadi",)),
    "poha": ((2.6, 3.5, 25.0), ("pohe", "flattened rice")),
    "upma": ((3.0, 6.0, 20.0), ()),
    "idli": ((3.4, 0.4, 24.0), ("idly", "idlis")),
    "dosa": ((3.9, 6.5, 25.0), ("dosai", "masala dosa")),
    # Pulses
    "dal": ((4.8, 2.5, 13.0), ("daal", "dhal", "toor dal", "arhar dal", "moong dal", "lentil curry")),
    "dal makhani": ((6.0, 9.0, 15.0), ("dal makhni",)),
    "rajma": ((8.7, 3.0, 22.0), ("kidney bean curry",)),
    "chole": ((7.0, 5.0, 20.0), ("chana masala", "chhole", "chickpea curry")),
    "sambar": ((2.5, 2.5, 8.0), ("sambhar",)),
    # Dairy
    "paneer": ((18.3, 20.8, 1.2), ("cottage cheese indian",)),
    "curd": ((3.1, 4.0, 4.0), ("dahi", "yoghurt", "yogurt", "plain curd")),
    "buttermilk": ((1.5, 1.0, 4.5), ("chaas", "chhaas")),
    "ghee": ((0.0, 99.5, 0.0), ("clarified butter",)),
    "lassi": ((2.6, 2.5, 13.0), ("sweet lassi",)),
    "chai": ((1.5, 1.8, 6.0), ("tea with milk", "masala chai", "milk tea")),
    # Vegetables and sides
    "aloo sabzi": ((2.0, 5.0, 17.0), ("aloo curry", "potato sabzi")),
    "bhindi": ((2.0, 6.0, 8.0), ("okra sabzi", "bhindi masala")),
    "palak paneer": ((8.0, 12.0, 6.0), ("saag paneer",)),
    "raita": ((2.5, 2.5, 4.5), ()),
    "papad": ((22.0, 2.0, 55.0), ("papadum", "appalam")),
    # Non vegetarian
    "chicken curry": ((12.0, 9.0, 4.0), ("murgh curry", "chicken masala")),
    "butter chicken": ((13.0, 14.0, 6.0), ("murgh makhani",)),
    "egg curry": ((8.0, 10.0, 5.0), ("anda curry",)),
    # Snacks and sweets
    "samosa": ((5.0, 17.0, 32.0), ("samosas",)),
    "pakora": ((5.0, 15.0, 25.0), ("bhaji", "bhajji", "pakoda")),
    "gulab jamun": ((4.0, 12.0, 45.0), ()),
    "halwa": ((4.0, 14.0, 40.0), ("sooji halwa", "gajar halwa")),
}


def _index() -> dict[str, str]:
    """Every name and alias, pointing at its entry."""
    lookup: dict[str, str] = {}
    for name, (_macros, aliases) in TABLE.items():
        lookup[name] = name
        for alias in aliases:
            lookup[alias] = name
    return lookup


NAMES = _index()


def look_up(food_name: str) -> FoodMatch | None:
    """
    Find an Indian staple, or return None so USDA gets its turn.

    Matching is exact on the name or an alias, then a contained match, so
    "masala dosa" and "hot dosa" both reach dosa. Nothing fuzzier than
    that: guessing wrong here is worse than handing over to USDA.
    """
    wanted = " ".join((food_name or "").lower().split())
    if not wanted:
        return None

    key = NAMES.get(wanted)

    if key is None and len(wanted.split()) <= MAX_WORDS_FOR_LOOSE_MATCH:
        # Longest alias first, so "dal makhani" is not swallowed by "dal",
        # and on whole words only: a plain substring test matched "curd"
        # inside "chicken breast and a cup of curd" and charged the whole
        # 150 grams to curd.
        for alias in sorted(NAMES, key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", wanted):
                key = NAMES[alias]
                break

    if key is None:
        return None

    protein, fat, carbs = TABLE[key][0]
    return FoodMatch(
        description=f"{key.title()} (home prepared, typical)",
        fdc_id=0,
        protein_per_100g=protein,
        fat_per_100g=fat,
        carbs_per_100g=carbs,
        source=SOURCE,
    )
