Dr. Nutritionist 
An AI-powered nutrition assistant that analyzes your daily food log to provide personalized feedback based on your health goals.

 About The Project
This project leverages the CrewAI agent framework to act as a personal nutritionist. It takes your profile information (age, gender, weight, etc.) and your daily food diary  to generate insights and recommendations. The goal is to help you achieve your fitness objectives, such as fat loss, by providing data-driven advice.

 Getting Started
To get a local copy up and running, follow these simple steps.

Prerequisites
Python 3.8+
kullanım
Update Your Profile
Modify the user_profile.json file with your personal information, including age, gender, height, weight, and primary goal.

Log Your Meals
Open daily_log.xlsx and input your daily food consumption. Ensure the columns include food, quantity, unit, protein, fat, and carbs.

Run the application
Execute the main script from your terminal. (Assuming your main file is named main.py)

Bash

python main.py
The application will then process your data and provide nutritional analysis and feedback.

 Project Structure
.
├── daily_log.xlsx      # Your daily food consumption log
├── user_profile.json   # Your personal profile and goals
├── requirements.txt    # List of Python dependencies
└── main.py             # (Assumed) The main script to run the AI agents
