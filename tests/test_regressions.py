"""
Bugs that reached a running system, kept as tests.

Each of these produced a wrong number rather than an error, which is the
kind that survives a demo and shows up in someone's day.
"""

from __future__ import annotations

import pytest

from dr_nutritionist import indian_foods, parsing
from dr_nutritionist.quantities import to_grams


def test_foods_joined_by_and_are_separate_items():
    """
    "150g chicken breast and a cup of curd" came through as one item.

    It then matched curd, and 150 grams of chicken was counted as 150
    grams of curd. Nothing failed, the total was simply wrong.
    """
    items = parsing.parse_meal("150g chicken breast and a cup of curd").items

    assert len(items) == 2
    assert items[0].name == "chicken breast"
    assert items[0].quantity == 150
    assert "curd" in items[1].name


@pytest.mark.parametrize("separator", [" and ", " with ", ", ", " plus ", "\n"])
def test_every_separator_people_use(separator):
    items = parsing.parse_meal(f"2 eggs{separator}150g rice").items
    assert len(items) == 2


def test_a_long_phrase_does_not_match_one_word_inside_it():
    """The table matched 'curd' anywhere in the text, however long."""
    assert indian_foods.look_up("chicken breast and a cup of curd on the side") is None
    assert indian_foods.look_up("a cup of curd") is not None


def test_a_word_containing_a_food_name_is_not_that_food():
    """Substring matching made anything containing 'dal' into lentils."""
    assert indian_foods.look_up("dalgona coffee") is None


def test_a_plural_count_uses_the_right_weight():
    """"2 rotis" fell through to the default of 100g each, so 200g instead of 80g."""
    grams, estimated = to_grams(2, "", "rotis")

    assert grams == 80
    assert estimated is True
