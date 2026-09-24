"""
The tool the nutrition agent is allowed to call.

This is what function calling actually is in this project. The agent
does not fetch anything itself. It emits a tool name and JSON arguments,
CrewAI matches that to this class, and this code makes the HTTP request.

Two details worth knowing, because both were deliberate:

1. The tool records every lookup it performs. The totals are then built
   from those recordings, not from the numbers the agent writes in its
   answer. A model transcribing "23.1 grams of protein" into its reply
   can get it wrong, and there is no reason to let it. The tool's own
   result is the source of truth.

2. A failed lookup returns a message rather than raising. A raised
   exception ends the crew. A message goes back to the agent, which can
   try a different wording, which is usually what a person would do.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, PrivateAttr

from crewai.tools import BaseTool

from .foods import look_up
from .usda import FoodMatch, UsdaError


class FoodQuery(BaseModel):
    """The arguments the model has to produce to call this tool."""

    food_name: str = Field(description="A single food, for example 'chicken breast' or 'banana'")


class UsdaLookupTool(BaseTool):
    name: str = "usda_lookup"
    description: str = (
        "Look up the macronutrients of one food. Checks a table of Indian "
        "staples first, then USDA FoodData Central. Returns protein, fat "
        "and carbohydrate in grams per 100 "
        "grams of that food. Call it once per food. Use it for every food, "
        "and never state nutrition figures from your own knowledge."
    )
    args_schema: type[BaseModel] = FoodQuery

    _found: dict[str, FoodMatch] = PrivateAttr(default_factory=dict)

    def _run(self, food_name: str) -> str:
        try:
            match = look_up(food_name)
        except UsdaError as problem:
            return f"No usable USDA entry for {food_name!r}: {problem}"

        self._found[food_name.strip().lower()] = match
        where = f"FDC {match.fdc_id}" if match.fdc_id else match.source
        return (
            f"{match.description} ({where}), per 100g: "
            f"protein {match.protein_per_100g}g, fat {match.fat_per_100g}g, "
            f"carbohydrate {match.carbs_per_100g}g"
        )

    # -- what the tool actually saw, for the code that does the maths ----

    def matches(self) -> dict[str, FoodMatch]:
        return dict(self._found)

    def match_for(self, food_name: str) -> FoodMatch | None:
        """
        The recorded result for a food.

        Falls back to a loose match, because the agent may look up
        "chicken breast" for an item the user wrote as "chicken".
        """
        wanted = food_name.strip().lower()
        if wanted in self._found:
            return self._found[wanted]
        for looked_up, match in self._found.items():
            if wanted in looked_up or looked_up in wanted:
                return match
        return None

    def forget(self) -> None:
        """Clear between runs, so one meal cannot borrow another's numbers."""
        self._found.clear()
