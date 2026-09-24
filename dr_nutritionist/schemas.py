"""
The shapes that pass between the agents.

Every handoff in this pipeline is a typed object, not free text. That is
deliberate. In a sequential crew each task's output becomes the next
task's input, so a vague or empty result does not fail, it just gets
accepted and built on. By the end you have a confident recommendation
resting on nothing, and no step ever looked like an error.

Validating the handoff turns that silent failure into a loud one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MealItem(BaseModel):
    """One food the caller mentioned, with how much of it."""

    name: str = Field(description="The food on its own, for example 'chicken breast'")
    quantity: float = Field(gt=0, description="How many of the unit")
    unit: str = Field(description="g, kg, ml, piece, or an empty string")

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("a meal item needs a food name")
        return cleaned


class ParsedMeal(BaseModel):
    """What the first agent produces: the meal broken into items."""

    items: list[MealItem]

    @field_validator("items")
    @classmethod
    def _at_least_one_item(cls, items: list[MealItem]) -> list[MealItem]:
        if not items:
            raise ValueError("no food items were found in that meal")
        return items


class FoodMacros(BaseModel):
    """Macros for one item, already scaled to the amount eaten."""

    name: str
    matched_as: str = Field(description="What the source matched, which is not always what was asked for")
    source: str = "USDA FoodData Central"
    grams: float
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0

    @property
    def calories(self) -> float:
        """Atwater factors: 4 kcal per gram of protein and carbohydrate, 9 for fat."""
        return self.protein_g * 4 + self.carbs_g * 4 + self.fat_g * 9


class DayTotals(BaseModel):
    """What the analysis agent produces: the day added up against targets."""

    items: list[FoodMacros]
    protein_g: float
    fat_g: float
    carbs_g: float
    calories: float
    target_protein_g: float
    target_fat_g: float
    target_carbs_g: float
    target_calories: float

    def share_of(self, macro: str) -> float:
        """How much of the target for that macro has been eaten, as a percentage."""
        eaten = getattr(self, f"{macro}_g")
        target = getattr(self, f"target_{macro}_g")
        return round(eaten / target * 100, 1) if target else 0.0


class Advice(BaseModel):
    """What the final agent produces. Written by the model, not calculated."""

    summary: str
    suggestions: list[str]

    @field_validator("summary")
    @classmethod
    def _summary_says_something(cls, value: str) -> str:
        if len(value.strip()) < 20:
            raise ValueError("the summary is too short to be a real answer")
        return value.strip()
