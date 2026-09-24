import os

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
        # The key comes from the environment. An earlier version of this
        # file had it written in the source, which is why it has been
        # revoked and replaced.
        self.api_key = api_key or os.environ.get("USDA_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "USDA_API_KEY is not set. Get a free key from "
                "https://fdc.nal.usda.gov/api-key-signup.html and put it in .env"
            )

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
