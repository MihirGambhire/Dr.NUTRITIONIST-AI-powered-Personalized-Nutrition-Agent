"""
The Streamlit front end.

It holds no logic of its own. It collects a profile and a meal, calls the
crew, and displays what came back, including what was skipped and whether
the model was involved at all. Those last two matter: a report that
quietly leaves a food out is worse than one that says it could not find
it.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dr_nutritionist import config, foods
from dr_nutritionist.crew import run
from dr_nutritionist.targets import ACTIVITY_FACTORS, GOAL_FACTORS, Profile, daily_targets

st.set_page_config(page_title="Dr. Nutritionist", page_icon="🥗", layout="centered")

st.title("Dr. Nutritionist")
st.caption(
    "Log a meal in plain English. Macros come from a table of Indian staples "
    "and from USDA FoodData Central, never from the model. Every row shows "
    "which source it came from. General information only, not dietetic advice."
)

with st.sidebar:
    st.header("About you")
    age = st.number_input("Age", min_value=13, max_value=100, value=21)
    gender = st.selectbox("Gender", ["male", "female"])
    height = st.number_input("Height (cm)", min_value=120.0, max_value=220.0, value=170.0)
    weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=75.0)
    goal = st.selectbox("Goal", list(GOAL_FACTORS))
    activity = st.selectbox("Activity", list(ACTIVITY_FACTORS), index=2)

    profile = Profile(
        age=int(age),
        gender=gender,
        height_cm=float(height),
        weight_kg=float(weight),
        goal=goal,
        activity=activity,
    )
    targets = daily_targets(profile)

    st.subheader("Your daily targets")
    st.write(
        f"**{targets.calories} kcal**  \n"
        f"{targets.protein_g}g protein, {targets.fat_g}g fat, {targets.carbs_g}g carbohydrate"
    )
    st.caption("Mifflin St Jeor, adjusted for activity and goal.")

    if not config.model_available():
        st.warning("No MISTRAL_API_KEY set, so meals are parsed by rule instead of by the model.")

meal = st.text_area(
    "What did you eat today?",
    placeholder="2 eggs, 150g chicken breast, a bowl of rice",
    height=100,
)

if st.button("Analyse", type="primary") and meal.strip():
    with st.spinner("Looking every food up in USDA..."):
        result = run(meal, profile)

    totals = result.totals

    st.subheader("The day")
    columns = st.columns(4)
    columns[0].metric("Calories", f"{totals.calories:.0f}", f"{totals.calories - totals.target_calories:+.0f}")
    columns[1].metric("Protein", f"{totals.protein_g:.0f}g", f"{totals.share_of('protein'):.0f}% of target")
    columns[2].metric("Fat", f"{totals.fat_g:.0f}g", f"{totals.share_of('fat'):.0f}% of target")
    columns[3].metric("Carbs", f"{totals.carbs_g:.0f}g", f"{totals.share_of('carbs'):.0f}% of target")

    st.subheader("What was counted")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Food": item.name,
                    "Matched as": item.matched_as,
                    "Source": item.source,
                    "Grams": item.grams,
                    "Protein": item.protein_g,
                    "Fat": item.fat_g,
                    "Carbs": item.carbs_g,
                }
                for item in totals.items
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("What it means")
    st.write(result.advice.summary)
    for suggestion in result.advice.suggestions:
        st.write(f"- {suggestion}")

    if result.skipped:
        st.warning("Not counted, because neither source had a close match:")
        for skip in result.skipped:
            st.write(f"- {skip}")

    for note in result.notes:
        st.info(note)

    counted = foods.sources_used_from_names([item.source for item in totals.items])
    st.caption(
        ", ".join(f"{count} from {source}" for source, count in counted.items())
        + (" | model used for language" if result.used_model else " | ran without a model")
    )
