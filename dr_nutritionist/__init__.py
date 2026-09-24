"""
Dr. Nutritionist.

The .env file is loaded here rather than in config.py, because the USDA
client reads its key straight from the environment and can be imported
on its own. Loading it at package level means every entry point, the
Streamlit app, the tests and a bare import, sees the same settings.
"""

from dotenv import load_dotenv

load_dotenv()
