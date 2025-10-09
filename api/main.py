import json
import os
from agents.input_agent import InputAgent
from agents.nutrition_agent import NutritionAgent
from agents.reporting_agent import ReportingAgent

PROFILE_FILE = 'user_profile.json'

def load_user_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            return json.load(f)
    else:
        profile = {
            "age": int(input("Enter your age: ")),
            "gender": input("Enter your gender: "),
            "height": float(input("Enter your height (cm): ")),
            "weight": float(input("Enter your weight (kg): ")),
            "goal": input("Enter your goal (lose fat/gain muscle/etc): ")
        }
        with open(PROFILE_FILE, 'w') as f:
            json.dump(profile, f)
        return profile

def main():
    print("\n Dr.Nutritionist is running!")
    profile = load_user_profile()
    print("👤 User profile:", profile)

    input_agent = InputAgent()
    nutrition_agent = NutritionAgent(api_key="ENTER YOUR API KEY HERE")
    reporting_agent = ReportingAgent()

    meals = []
    for i in range(3):
        meal_input = input(f"\n🍽️ Logging meal {i + 1}:\nEnter your meal (comma-separated, e.g. 2 eggs, 150g chicken): ")
        parsed = input_agent.parse_meal(meal_input)
        for item in parsed:
            food_data = nutrition_agent.get_nutrition(item['name'])
            if food_data:
                scale = nutrition_agent.get_scale_factor(item, food_data)
                meal_entry = {
                    "food": item['name'],
                    "quantity": item['quantity'],
                    "unit": item['unit'],
                    "protein": round(food_data.get("Protein", 0) * scale, 2),
                    "fat": round(food_data.get("Total lipid (fat)", 0) * scale, 2),
                    "carbs": round(food_data.get("Carbohydrate, by difference", 0) * scale, 2)
                }
                meals.append(meal_entry)
                print(f"  ✅ Added: {meal_entry}")
            else:
                print(f"  ⚠️ No data for: {item['name']}")

    insights, deficiency = reporting_agent.analyze(meals)
    print("\n✅ Nutrient breakdown:")
    for k, v in insights.items():
        print(f"  {k.capitalize()}: {v}")
    if deficiency:
        print("\n⚠️ Possible deficiencies:")
        for d in deficiency:
            print(f"  - {d}")
    else:
        print("\n🎉 You hit your targets well!")

    reporting_agent.save_to_excel(meals)
    reporting_agent.plot_macros(insights)

if __name__ == "__main__":
    main()
