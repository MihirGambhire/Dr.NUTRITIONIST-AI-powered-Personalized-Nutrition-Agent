"""
Adding the day up.

None of this is done by the model. The model reads a meal in English and
later writes the advice in English, which is what it is good at. The
arithmetic in between is ordinary Python, because a number that comes out
of a language model cannot be checked and a number that comes out of a
function can.
"""

from __future__ import annotations

from .quantities import scale_from_100g, to_grams
from .schemas import DayTotals, FoodMacros, MealItem
from .targets import Targets
from .foods import look_up
from .usda import FoodMatch, UsdaError


def macros_for(item: MealItem, match: FoodMatch) -> FoodMacros:
    """Scale one USDA match to the amount actually eaten."""
    grams, _estimated = to_grams(item.quantity, item.unit, item.name)
    return FoodMacros(
        name=item.name,
        matched_as=match.description,
        source=match.source,
        grams=round(grams, 1),
        protein_g=scale_from_100g(match.protein_per_100g, grams),
        fat_g=scale_from_100g(match.fat_per_100g, grams),
        carbs_g=scale_from_100g(match.carbs_per_100g, grams),
    )


def look_up_all(items: list[MealItem], lookup=look_up) -> tuple[list[FoodMacros], list[str]]:
    """
    Look every item up, and keep going when one of them fails.

    A single unknown food should not lose the whole meal, so failures are
    collected and returned alongside the results. The user is told what
    was skipped, rather than being given a total that quietly leaves
    something out.
    """
    found: list[FoodMacros] = []
    skipped: list[str] = []
    for item in items:
        try:
            found.append(macros_for(item, lookup(item.name)))
        except UsdaError as problem:
            skipped.append(f"{item.name}: {problem}")
    return found, skipped


def total_day(items: list[FoodMacros], targets: Targets) -> DayTotals:
    """Add the items up and set them against the day's targets."""
    protein = round(sum(i.protein_g for i in items), 1)
    fat = round(sum(i.fat_g for i in items), 1)
    carbs = round(sum(i.carbs_g for i in items), 1)
    return DayTotals(
        items=items,
        protein_g=protein,
        fat_g=fat,
        carbs_g=carbs,
        calories=round(protein * 4 + carbs * 4 + fat * 9, 1),
        target_protein_g=targets.protein_g,
        target_fat_g=targets.fat_g,
        target_carbs_g=targets.carbs_g,
        target_calories=targets.calories,
    )


# Below this share of a target, the day is short of that macro. Set at 80
# percent because hitting a target exactly never happens, and flagging
# every small shortfall makes the report useless.
SHORTFALL = 0.8


def shortfalls(totals: DayTotals) -> list[str]:
    """Which macros came in low. Plain statements, never advice."""
    short = []
    for macro, label in (("protein", "protein"), ("fat", "fat"), ("carbs", "carbohydrate")):
        eaten = getattr(totals, f"{macro}_g")
        target = getattr(totals, f"target_{macro}_g")
        if target and eaten < target * SHORTFALL:
            short.append(f"{label} is at {totals.share_of(macro)} percent of target")
    return short
