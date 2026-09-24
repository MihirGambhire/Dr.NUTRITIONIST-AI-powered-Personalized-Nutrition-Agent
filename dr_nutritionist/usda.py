"""
The USDA FoodData Central lookup.

This is the grounding layer. Every macro number in the final report comes
from here, never from the model, for the same reason a search engine
beats recall: a language model asked how much protein is in 150g of
chicken will produce a plausible number, and plausible is not the same as
right.

Kept free of any agent framework so it can be tested on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
TIMEOUT_SECONDS = 15

# USDA's names for the three macros. They are stable, but spelled the way
# a chemist would spell them.
PROTEIN = "Protein"
FAT = "Total lipid (fat)"
CARBS = "Carbohydrate, by difference"

# Whole foods first. Branded entries are per serving and full of near
# duplicates, which makes them a poor default for "150g of chicken".
#
# "Survey (FNDDS)" used to be in this list and was taken out after an
# intermittent bug: identical requests returned 400 perhaps a third of
# the time, with an HTML error page rather than the API's own JSON. The
# cause was the brackets in that value, which some of the nodes behind
# the API reject and others accept, so the same request succeeded or
# failed depending on which one answered. Survey foods are still
# reachable through the unfiltered second search below.
PREFERRED_DATA_TYPES = "Foundation,SR Legacy"

# One session for the process, so connections are reused rather than
# reopened for every food in a meal.
_session = requests.Session()


class UsdaError(RuntimeError):
    """The lookup could not be completed. Raised rather than returning None."""


@dataclass(frozen=True)
class FoodMatch:
    """One food from USDA, with macros per 100 grams."""

    description: str
    fdc_id: int
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    source: str = "USDA FoodData Central"


def _api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get("USDA_API_KEY", "")
    if not key:
        raise UsdaError(
            "USDA_API_KEY is not set. Get a free key from "
            "https://fdc.nal.usda.gov/api-key-signup.html and put it in .env"
        )
    return key


# USDA search ranks by its own relevance, and the top hit is often not
# the food anyone meant: "banana" returned banana powder, "oats" returned
# oat oil, and "milk" returned milk crackers. Since every macro in the
# report comes from this match, picking the wrong food quietly poisons
# the whole day, so the candidates are scored here rather than trusting
# the order they arrive in.
_PROCESSED = (
    "dehydrated", "powder", "powdered", "dried", "juice", "oil", "crackers",
    "cracker", "breaded", "fried", "canned", "candied", "syrup", "infant",
    "baby food", "formula", "snack", "chips", "sweetened", "concentrate",
    "flavored", "flavoured", "imitation", "substitute",
)

# Whole foods are preferred, then survey data, then branded entries,
# which are per serving and full of near duplicates.
_DATA_TYPE_RANK = {"Foundation": 3, "SR Legacy": 2, "Survey (FNDDS)": 1}

# Words naming a part of a food rather than the food: "rice bran" for
# rice, "egg white" for eggs. Penalised unless the caller asked for that
# part by name, in which case it is exactly what they meant.
_PARTS = (
    "bran", "germ", "hull", "husk", "yolk", "white", "skin", "peel", "leaf",
    "leave", "flour", "meal", "starch", "sprout", "seed", "shell",
)


def _words(text: str) -> list[str]:
    """Lower case words, with a trailing plural s removed so banana matches bananas."""
    cleaned = "".join(character if character.isalnum() else " " for character in text.lower())
    return [word[:-1] if len(word) > 3 and word.endswith("s") else word for word in cleaned.split()]


def _score(query: str, food: dict) -> float:
    """
    How well this candidate answers the query. Higher is better.

    Every word of the query has to appear, so "chicken breast" cannot
    match "chicken soup". After that, shorter and less processed wins,
    because "Bananas, raw" is what someone means by "banana".
    """
    description = food.get("description", "")
    wanted = _words(query)
    got = _words(description)
    if not wanted or not all(word in got for word in wanted):
        return 0.0

    score = 10.0
    score += _DATA_TYPE_RANK.get(food.get("dataType", ""), 0)
    # Compared word by word rather than by string, so "eggs" still
    # rewards "Egg, whole, raw" for leading with the food itself.
    if got and wanted and got[0] == wanted[0]:
        score += 3
    if "raw" in got:
        score += 2

    # Each extra word is another qualifier the caller did not ask for.
    score -= 0.6 * max(len(got) - len(wanted), 0)
    score -= 3 * sum(1 for junk in _PROCESSED if junk in description.lower())
    score -= 2.5 * sum(1 for part in _PARTS if part in got and part not in wanted)
    return score


def _macros(food: dict) -> dict[str, float]:
    found = {}
    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName")
        if name in (PROTEIN, FAT, CARBS):
            found[name] = float(nutrient.get("value") or 0.0)
    return found


def look_up(food_name: str, api_key: str | None = None, session=None) -> FoodMatch:
    """
    Find one food and return its macros per 100 grams.

    Raises rather than returning None, so a failed lookup cannot be
    quietly treated as a food with no calories in it.
    """
    query = (food_name or "").strip()
    if not query:
        raise UsdaError("no food name was given")

    http = session or _session
    key = _api_key(api_key)

    def search(data_types: str | None) -> list[dict]:
        # Enough candidates for the scoring to have a real choice:
        # the plain version of a food is often not in the first ten.
        params = {"query": query, "api_key": key, "pageSize": 25}
        if data_types:
            params["dataType"] = data_types
        try:
            response = http.get(SEARCH_URL, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as problem:
            raise UsdaError(f"could not reach USDA: {problem}") from problem

        if response.status_code == 429:
            raise UsdaError("USDA rate limit reached, try again shortly")
        if response.status_code != 200:
            raise UsdaError(f"USDA returned {response.status_code}")
        return response.json().get("foods") or []

    # Whole foods first, then anything at all. A dish like "dal" exists
    # only as a branded or survey entry, and returning nothing for it
    # would be worse than returning an approximate match.
    foods = search(PREFERRED_DATA_TYPES) or search(None)
    if not foods:
        raise UsdaError(f"no USDA match for {query!r}")

    # Only candidates carrying all three macros are usable: the results
    # include supplements and spices with a protein figure and nothing
    # else, and a missing macro would silently count as zero.
    usable = [(food, _macros(food)) for food in foods]
    usable = [(food, macros) for food, macros in usable if len(macros) == 3]
    if not usable:
        raise UsdaError(f"USDA had no complete macro data for {query!r}")

    best, macros = max(usable, key=lambda pair: _score(query, pair[0]))

    # A zero score means no candidate contained the words that were asked
    # for. Better to say so than to return a branded snack that happens
    # to share a word with the query.
    if _score(query, best) <= 0:
        raise UsdaError(f"no close USDA match for {query!r}")

    return FoodMatch(
        description=best.get("description", query),
        fdc_id=int(best.get("fdcId", 0)),
        protein_per_100g=macros[PROTEIN],
        fat_per_100g=macros[FAT],
        carbs_per_100g=macros[CARBS],
    )
