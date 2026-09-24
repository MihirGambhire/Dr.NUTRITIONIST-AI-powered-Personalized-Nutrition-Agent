"""
Tests for the parts that must be right whatever the model does.

None of these need an API key or a network connection. The USDA lookup
is replaced with a stub, because the point of these tests is the
arithmetic and the handling of failure, not whether USDA is up.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dr_nutritionist import parsing, report
from dr_nutritionist.quantities import scale_from_100g, to_grams
from dr_nutritionist.schemas import Advice, MealItem, ParsedMeal
from dr_nutritionist.targets import Profile, basal_rate, daily_targets
from dr_nutritionist.usda import FoodMatch, UsdaError

CHICKEN = FoodMatch(
    description="Chicken, broilers or fryers, breast, meat only, raw",
    fdc_id=171077,
    protein_per_100g=22.5,
    fat_per_100g=2.6,
    carbs_per_100g=0.0,
)
EGG = FoodMatch(
    description="Egg, whole, raw, fresh",
    fdc_id=748967,
    protein_per_100g=12.6,
    fat_per_100g=9.5,
    carbs_per_100g=0.7,
)


def fake_lookup(food_name: str) -> FoodMatch:
    lowered = food_name.lower()
    if "chicken" in lowered:
        return CHICKEN
    if "egg" in lowered:
        return EGG
    raise UsdaError(f"no USDA match for {food_name!r}")


# -- amounts ------------------------------------------------------------


@pytest.mark.parametrize(
    "quantity,unit,food,grams,estimated",
    [
        (150, "g", "chicken", 150, False),
        (1.5, "kg", "rice", 1500, False),
        (2, "piece", "egg", 100, True),
        (2, "", "eggs", 100, True),
        (1, "", "something nobody has heard of", 100, True),
    ],
)
def test_amounts_become_grams(quantity, unit, food, grams, estimated):
    assert to_grams(quantity, unit, food) == (grams, estimated)


def test_usda_values_scale_from_one_hundred_grams():
    assert scale_from_100g(22.5, 150) == 33.75


# -- targets ------------------------------------------------------------


def test_targets_come_from_the_person_not_a_constant():
    """The first version compared everyone against the same 150g of protein."""
    small = Profile(age=21, gender="female", height_cm=155, weight_kg=50, goal="maintain")
    large = Profile(age=21, gender="male", height_cm=190, weight_kg=95, goal="gain muscle")

    assert daily_targets(large).calories > daily_targets(small).calories
    assert daily_targets(large).protein_g > daily_targets(small).protein_g


def test_losing_fat_gives_fewer_calories_than_maintaining():
    losing = Profile(age=21, gender="male", height_cm=170, weight_kg=75, goal="lose fat")
    maintaining = Profile(age=21, gender="male", height_cm=170, weight_kg=75, goal="maintain")
    assert daily_targets(losing).calories < daily_targets(maintaining).calories


def test_basal_rate_matches_mifflin_st_jeor_by_hand():
    # 10*75 + 6.25*170 - 5*21 + 5 = 1712.5
    profile = Profile(age=21, gender="male", height_cm=170, weight_kg=75)
    assert basal_rate(profile) == pytest.approx(1712.5)


# -- the day ------------------------------------------------------------


def test_macros_are_scaled_to_what_was_eaten():
    item = MealItem(name="chicken breast", quantity=150, unit="g")
    macros = report.macros_for(item, CHICKEN)

    assert macros.grams == 150
    assert macros.protein_g == pytest.approx(33.75)
    assert macros.matched_as.startswith("Chicken")


def test_one_unknown_food_does_not_lose_the_whole_meal():
    items = [
        MealItem(name="chicken breast", quantity=150, unit="g"),
        MealItem(name="zzzz nonsense", quantity=1, unit=""),
        MealItem(name="eggs", quantity=2, unit="piece"),
    ]
    found, skipped = report.look_up_all(items, lookup=fake_lookup)

    assert [f.name for f in found] == ["chicken breast", "eggs"]
    assert len(skipped) == 1 and "zzzz nonsense" in skipped[0]


def test_calories_come_from_the_macros_not_from_a_model():
    items = [MealItem(name="chicken breast", quantity=100, unit="g")]
    found, _ = report.look_up_all(items, lookup=fake_lookup)
    totals = report.total_day(found, daily_targets(Profile(21, "male", 170, 75)))

    # 22.5g protein and 2.6g fat: 22.5*4 + 2.6*9 = 113.4
    assert totals.calories == pytest.approx(113.4, abs=0.2)


def test_a_short_day_is_reported_as_short():
    items = [MealItem(name="eggs", quantity=1, unit="piece")]
    found, _ = report.look_up_all(items, lookup=fake_lookup)
    totals = report.total_day(found, daily_targets(Profile(21, "male", 170, 75)))

    short = report.shortfalls(totals)
    assert any("protein" in s for s in short)


# -- parsing without a model -------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("150g chicken", ("chicken", 150.0, "g")),
        ("2 eggs", ("eggs", 2.0, "")),
        ("1.5 kg rice", ("rice", 1.5, "kg")),
        ("banana", ("banana", 1.0, "")),
    ],
)
def test_the_fallback_parser_reads_tidy_input(text, expected):
    item = parsing.parse_meal(text).items[0]
    assert (item.name, item.quantity, item.unit) == expected


def test_an_empty_meal_fails_loudly():
    """Silence here would become a day with no calories in it."""
    with pytest.raises(ValidationError):
        parsing.parse_meal("   ")


# -- the typed handoffs -------------------------------------------------


def test_a_handoff_with_no_items_is_rejected():
    with pytest.raises(ValidationError):
        ParsedMeal(items=[])


def test_a_handoff_with_a_blank_food_name_is_rejected():
    with pytest.raises(ValidationError):
        MealItem(name="  ", quantity=1, unit="g")


def test_a_negative_quantity_is_rejected():
    with pytest.raises(ValidationError):
        MealItem(name="rice", quantity=-1, unit="g")


def test_an_empty_summary_is_rejected():
    """An agent returning almost nothing is the failure that must not pass."""
    with pytest.raises(ValidationError):
        Advice(summary="ok", suggestions=[])
