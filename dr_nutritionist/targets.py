"""
Daily targets, worked out from the person rather than hardcoded.

The first version of this project compared everyone against 150g of
protein, 50g of fat and 150g of carbohydrate, whoever they were. It
collected an age, a height, a weight and a goal, and then ignored all
four.

These are the standard equations instead. They are still estimates, and
the README says so: this is a demo, not dietetic advice.
"""

from __future__ import annotations

from dataclasses import dataclass

# Mifflin St Jeor, the equation most commonly used for resting energy.
_MALE_OFFSET = 5
_FEMALE_OFFSET = -161

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very active": 1.9,
}

# Calorie adjustment for the goal. Roughly a 20 percent deficit or a 10
# percent surplus, which are the usual conservative figures.
GOAL_FACTORS = {
    "lose fat": 0.8,
    "maintain": 1.0,
    "gain muscle": 1.1,
}

CALORIES_PER_GRAM = {"protein": 4, "carbs": 4, "fat": 9}


@dataclass(frozen=True)
class Profile:
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    goal: str = "maintain"
    activity: str = "moderate"


@dataclass(frozen=True)
class Targets:
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


def basal_rate(profile: Profile) -> float:
    """Calories burned at rest, by Mifflin St Jeor."""
    offset = _MALE_OFFSET if profile.gender.strip().lower().startswith("m") else _FEMALE_OFFSET
    return (
        10 * profile.weight_kg
        + 6.25 * profile.height_cm
        - 5 * profile.age
        + offset
    )


def daily_targets(profile: Profile) -> Targets:
    """
    Calories for the goal, then split into macros.

    Protein is set per kilogram of bodyweight rather than as a percentage
    of calories, because protein need tracks body size, not intake. Fat
    takes 25 percent of calories, and carbohydrate takes whatever is
    left, which is the usual way round.
    """
    activity = ACTIVITY_FACTORS.get(profile.activity.strip().lower(), 1.55)
    goal = GOAL_FACTORS.get(profile.goal.strip().lower(), 1.0)
    calories = basal_rate(profile) * activity * goal

    protein_per_kg = 1.6 if profile.goal.strip().lower() != "maintain" else 1.2
    protein_g = profile.weight_kg * protein_per_kg
    fat_g = calories * 0.25 / CALORIES_PER_GRAM["fat"]
    carbs_calories = calories - protein_g * CALORIES_PER_GRAM["protein"] - fat_g * CALORIES_PER_GRAM["fat"]
    carbs_g = max(carbs_calories, 0) / CALORIES_PER_GRAM["carbs"]

    return Targets(
        calories=round(calories),
        protein_g=round(protein_g),
        fat_g=round(fat_g),
        carbs_g=round(carbs_g),
    )
