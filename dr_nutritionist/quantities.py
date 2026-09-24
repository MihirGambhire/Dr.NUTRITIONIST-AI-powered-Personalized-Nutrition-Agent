"""
Turning "2 eggs" or "150g chicken" into grams.

USDA returns nutrients per 100 grams, so everything has to reach grams
before it can be scaled. Pieces are the awkward case: an egg is not a
unit of mass, so a typical weight is used and the assumption is recorded
rather than hidden.
"""

from __future__ import annotations

GRAMS_PER_UNIT = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "ml": 1.0,  # close enough for water based foods, wrong for oils
    "l": 1000.0,
}

# Typical edible weights, used only when someone counts instead of weighing.
# These are averages, so the result is an estimate and the report says so.
TYPICAL_PIECE_GRAMS = {
    "egg": 50.0,
    "eggs": 50.0,
    "banana": 118.0,
    "apple": 182.0,
    "bread": 30.0,
    "roti": 40.0,
    "chapati": 40.0,
    "slice": 30.0,
    "scoop": 30.0,
    "cup": 240.0,
}

DEFAULT_PIECE_GRAMS = 100.0


def to_grams(quantity: float, unit: str, food_name: str = "") -> tuple[float, bool]:
    """
    Convert an amount to grams.

    Returns the grams and whether the answer was estimated, so the caller
    can tell the user which numbers are weighed and which are guessed.
    """
    unit = (unit or "").strip().lower()

    if unit in GRAMS_PER_UNIT:
        return quantity * GRAMS_PER_UNIT[unit], False

    # A count, either "2 eggs" or a bare "2" where the food names itself.
    # Plurals are trimmed, because "2 rotis" fell through to the default
    # of 100g each and counted two and a half times what it should have.
    for word in (unit, *food_name.lower().split()):
        for candidate in (word, word[:-1] if word.endswith("s") else word):
            if candidate in TYPICAL_PIECE_GRAMS:
                return quantity * TYPICAL_PIECE_GRAMS[candidate], True

    return quantity * DEFAULT_PIECE_GRAMS, True


def scale_from_100g(per_100g: float, grams: float) -> float:
    """USDA values are per 100 grams. Scale one to the amount actually eaten."""
    return round(per_100g * grams / 100.0, 2)
