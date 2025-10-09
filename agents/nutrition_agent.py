from crewai import Agent
import requests

class NutritionAgent(Agent):
    def __init__(self, api_key):
        super().__init__(
            name="NutritionAgent",
            role="Fetches nutrition information",
            goal="Retrieve macro and micronutrient details from the USDA API.",
            backstory="This agent connects to the USDA FoodData Central to fetch accurate nutrition facts for foods logged by the user."
        )
        self.api_key = "PCxfmnrVtnEzYpdZUYPAAjNQtL0Y1iDaWn1KXkJu"  # ✅ Save the key

    def search_food(self, query):
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={query}&api_key={self.api_key}"
        response = requests.get(url)
        return response.json()

    def get_nutrition(self, food_name):
        results = self.search_food(food_name)
        if results.get("foods"):
            nutrients = {}
            food = results["foods"][0]
            for nutrient in food.get("foodNutrients", []):
                nutrients[nutrient.get("nutrientName")] = nutrient.get("value")
            return nutrients
        else:
            return None
