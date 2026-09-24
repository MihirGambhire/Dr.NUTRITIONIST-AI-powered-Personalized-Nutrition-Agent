"""
One place to ask "what is in this food".

Two sources sit behind this: a small table of Indian staples, and USDA
FoodData Central. The table is tried first, because the people using this
log roti and dal, and USDA answers those badly. USDA takes everything
else, which is most of the world's food.

Everything else in the project calls this, not either source directly, so
adding a third source later is a change in this file alone. The match
carries the name of the source that produced it, and the UI shows it, so
a number can always be traced back to where it came from.
"""

from __future__ import annotations

from . import indian_foods
from .usda import FoodMatch, UsdaError
from .usda import look_up as usda_look_up


def look_up(food_name: str) -> FoodMatch:
    """
    Macros per 100 grams for one food.

    Raises UsdaError when neither source can answer, rather than
    returning None, because a food that quietly comes back empty would be
    counted as a food with nothing in it.
    """
    local = indian_foods.look_up(food_name)
    if local is not None:
        return local
    return usda_look_up(food_name)


def sources_used(matches: list[FoodMatch]) -> dict[str, int]:
    """How many foods came from each source. Shown under the day's table."""
    counted: dict[str, int] = {}
    for match in matches:
        counted[match.source] = counted.get(match.source, 0) + 1
    return counted


def sources_used_from_names(sources: list[str]) -> dict[str, int]:
    """Same count, from the source names the report already carries."""
    counted: dict[str, int] = {}
    for source in sources:
        counted[source] = counted.get(source, 0) + 1
    return counted
