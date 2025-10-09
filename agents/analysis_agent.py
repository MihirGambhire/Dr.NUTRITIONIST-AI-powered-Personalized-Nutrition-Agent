from crewai import Agent

class AnalysisAgent(Agent):
    def __init__(self):
        super().__init__(
            name="AnalysisAgent",
            role="Analyzes nutrition data",
            goal="Calculate daily macro and micro totals, compare with goals.",
            backstory="This agent processes all nutrition info to create daily summaries and checks alignment with the user's goals."
        )

    def analyze(self, meals_nutrition):
        total_protein = sum(item.get("protein", 0) for item in meals_nutrition)
        total_fat = sum(item.get("fat", 0) for item in meals_nutrition)
        total_carbs = sum(item.get("carbs", 0) for item in meals_nutrition)
        return {
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carbs": total_carbs,
        }
