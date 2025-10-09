from crewai import Agent

class InputAgent(Agent):
    def __init__(self):
        super().__init__(
            name="InputAgent",
            role="Takes input from the user",
            goal="Parse meals into food items with quantities.",
            backstory="Helps users easily log meals with realistic quantities and units."
        )

    def parse_meal(self, meal_input):
        items = []
        for part in meal_input.split(","):
            part = part.strip().lower()
            tokens = part.split()
            quantity = 1
            unit = ""
            food_name = ""

            for token in tokens:
                if token.replace('.', '', 1).isdigit():
                    quantity = float(token)
                elif token in ["grams", "gram", "g", "kg", "ml", "scoop", "scoops", "piece", "pieces", "egg", "eggs"]:
                    unit = token
                else:
                    food_name += token + " "

            items.append({
                "name": food_name.strip(),
                "quantity": quantity,
                "unit": unit
            })
        return items
