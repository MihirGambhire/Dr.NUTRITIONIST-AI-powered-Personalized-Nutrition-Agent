from crewai import Agent
import pandas as pd
import matplotlib.pyplot as plt

class ReportingAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ReportingAgent",
            role="Analyzes logged meals",
            goal="Generate daily nutrition reports and insights.",
            backstory="Turns raw meal data into actionable insights."
        )

    def analyze(self, meals):
        total_protein = sum(m['protein'] for m in meals)
        total_fat = sum(m['fat'] for m in meals)
        total_carbs = sum(m['carbs'] for m in meals)
        total_calories = total_protein * 4 + total_fat * 9 + total_carbs * 4

        protein_goal = 150
        fat_goal = 50
        carbs_goal = 150

        insights = {
            "protein": f"{total_protein}g ({round(total_protein / protein_goal * 100, 1)}%)",
            "fat": f"{total_fat}g ({round(total_fat / fat_goal * 100, 1)}%)",
            "carbs": f"{total_carbs}g ({round(total_carbs / carbs_goal * 100, 1)}%)",
            "calories": f"{total_calories} kcal"
        }

        deficiency = []
        if total_protein < protein_goal:
            deficiency.append("Low protein")
        if total_fat < fat_goal * 0.8:
            deficiency.append("Low fat")
        if total_carbs < carbs_goal * 0.8:
            deficiency.append("Low carbs")

        return insights, deficiency

    def save_to_excel(self, meals):
        df = pd.DataFrame(meals)
        df.to_excel("daily_log.xlsx", index=False)
        print("💾 Saved log to daily_log.xlsx")

    def plot_macros(self, insights):
        sizes = [float(insights['protein'].split()[0]), float(insights['fat'].split()[0]), float(insights['carbs'].split()[0])]
        labels = ["Protein", "Fat", "Carbs"]
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title("Macro Distribution")
        plt.show()
