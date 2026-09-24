"""
Reading a meal without a model.

The crew uses an LLM to parse "two eggs and a roti with some dal", which
is what it is for. This is the fallback for when the model is out of
quota or unreachable, so the app degrades instead of stopping.

It only handles the tidy shape, "2 eggs, 150g chicken", and it says so
rather than guessing at the messy ones.
"""

from __future__ import annotations

import re

from .quantities import GRAMS_PER_UNIT
from .schemas import MealItem, ParsedMeal

# Words that count something without naming it. Deliberately separate
# from the list of typical weights, because that list also holds foods:
# in "2 eggs", "eggs" is the food, not the unit, and reading it as a unit
# leaves an item with no name at all.
COUNT_UNITS = {"piece", "pieces", "slice", "slices", "scoop", "scoops", "cup", "cups"}
KNOWN_UNITS = set(GRAMS_PER_UNIT) | COUNT_UNITS

# "150g chicken", "2 eggs", "1.5 kg rice". The number may be stuck to the
# unit, which is how people actually type it.
_AMOUNT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-z]+)?\s*(.*)$", re.IGNORECASE)


# People separate foods with more than commas. A meal split only on
# commas turned "150g chicken breast and a cup of curd" into one item,
# which then matched curd and counted 150g of it. One separator missing
# was enough to put the wrong food in the day's totals.
_SEPARATORS = re.compile(
    r",|\band\b|\bwith\b|\bplus\b|\+|\n",
    re.IGNORECASE,
)


def _split_items(text: str) -> list[str]:
    return [part for part in _SEPARATORS.split(text or "") if part.strip()]


def parse_meal(text: str) -> ParsedMeal:
    """Split a comma separated meal into items. Raises if nothing is found."""
    items: list[MealItem] = []

    for part in _split_items(text):
        part = part.strip().lower()
        if not part:
            continue

        match = _AMOUNT.match(part)
        if not match:
            # No number at all, so treat it as one of whatever it is.
            items.append(MealItem(name=part, quantity=1, unit=""))
            continue

        amount, maybe_unit, rest = match.groups()
        unit = (maybe_unit or "").strip()
        name = rest.strip()

        # "2 eggs" puts the food where the unit would be.
        if unit and unit not in KNOWN_UNITS:
            name = f"{unit} {name}".strip()
            unit = ""

        if not name:
            continue

        items.append(MealItem(name=name, quantity=float(amount), unit=unit))

    return ParsedMeal(items=items)
