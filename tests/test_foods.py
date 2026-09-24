"""
Tests for the two source lookup.

None of these touch the network. The USDA half is stubbed, because what
is being tested is which source answers and whether the table is sane,
not whether USDA is up.
"""

from __future__ import annotations

import pytest

from dr_nutritionist import foods, indian_foods
from dr_nutritionist.indian_foods import TABLE
from dr_nutritionist.usda import FoodMatch, UsdaError

# Grams of macro in 100 grams of food. Anything above this is a typo:
# only pure fat and pure sugar come close, and a fourth column, water,
# always takes some of the room.
MAX_MACROS_PER_100G = 100.0


@pytest.mark.parametrize("name", sorted(TABLE))
def test_every_indian_entry_is_physically_possible(name):
    """One misplaced decimal point would quietly distort every day it appears in."""
    protein, fat, carbs = TABLE[name][0]

    assert all(value >= 0 for value in (protein, fat, carbs)), name
    assert protein + fat + carbs <= MAX_MACROS_PER_100G, name

    calories = protein * 4 + fat * 9 + carbs * 4
    assert calories <= 900, f"{name} works out at {calories} kcal per 100g"


@pytest.mark.parametrize("name", sorted(TABLE))
def test_no_alias_points_at_two_different_foods(name):
    """An alias claimed twice would silently hand one food another's macros."""
    for alias in TABLE[name][1]:
        assert indian_foods.NAMES[alias] == name


@pytest.mark.parametrize(
    "asked,expected",
    [
        ("roti", "roti"),
        ("chapati", "roti"),
        ("2 rotis", "roti"),
        ("dahi", "curd"),
        ("masala dosa", "dosa"),
        ("dal makhani", "dal makhani"),  # not swallowed by "dal"
        ("toor dal", "dal"),
        ("paneer", "paneer"),
    ],
)
def test_indian_staples_are_found_by_the_names_people_type(asked, expected):
    match = indian_foods.look_up(asked)
    assert match is not None, asked
    assert match.description.lower().startswith(expected)


@pytest.mark.parametrize("asked", ["chicken breast", "broccoli", "cheddar cheese"])
def test_food_that_is_not_indian_is_left_to_usda(asked):
    assert indian_foods.look_up(asked) is None


def test_the_indian_table_answers_before_usda(monkeypatch):
    def should_not_run(_name):
        raise AssertionError("USDA was called for a food the table already knows")

    monkeypatch.setattr(foods, "usda_look_up", should_not_run)
    match = foods.look_up("roti")

    assert match.source == indian_foods.SOURCE
    assert match.protein_per_100g > 0


def test_usda_answers_for_everything_else(monkeypatch):
    stub = FoodMatch(
        description="Broccoli, raw",
        fdc_id=747447,
        protein_per_100g=2.6,
        fat_per_100g=0.3,
        carbs_per_100g=6.6,
    )
    monkeypatch.setattr(foods, "usda_look_up", lambda name: stub)

    match = foods.look_up("broccoli")
    assert match.source == "USDA FoodData Central"


def test_a_food_neither_source_knows_raises(monkeypatch):
    """Returning nothing would count the food as having no calories in it."""
    def nothing(name):
        raise UsdaError(f"no close USDA match for {name!r}")

    monkeypatch.setattr(foods, "usda_look_up", nothing)
    with pytest.raises(UsdaError):
        foods.look_up("zzqqxx nonsense")


def test_sources_are_counted_for_the_report():
    matches = [
        indian_foods.look_up("roti"),
        indian_foods.look_up("dal"),
        FoodMatch(description="Broccoli, raw", fdc_id=1, protein_per_100g=2.6, fat_per_100g=0.3, carbs_per_100g=6.6),
    ]
    counted = foods.sources_used(matches)

    assert counted[indian_foods.SOURCE] == 2
    assert counted["USDA FoodData Central"] == 1
