# llm_processor.py (FINAL VERSION: GEMINI API + INTERNAL MOCK NUTRIENTS)

import json
import pandas as pd
from google import genai
from google.genai import types

# --- Configuration: REPLACE 'YOUR_API_KEY_HERE' with your actual key ---
API_KEY = "AIzaSyDUo28hUMwckFaln_1cJmsZ_OcWkB1sJys" 
# ------------------------------------------------------------------------

# Initialize the Gemini Client
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Error initializing Gemini client: {e}. Check your API key.")
    client = None

# This prompt template guides the LLM on what kind of structured output to produce.
LLM_PROMPT = """
You are an expert nutritional data parser. Your task is to extract all food items and their estimated quantities from a user's free-text meal description.

Your response MUST be ONLY a JSON list of objects, one for each food item. Do not include any other text or markdown formatting outside the JSON.
For vague items (e.g., 'a cup of coffee'), estimate the quantity in grams (g) based on standard serving sizes.

Example Input: "I had a bowl of rice and some chicken"
Example Output:
[
  {"food_name": "cooked white rice", "quantity_g": 150},
  {"food_name": "grilled chicken breast", "quantity_g": 100}
]

Meal Description to Analyze: '{meal_description}'
"""

def get_llm_meal_interpretation(meal_description: str) -> list:
    """
    Function that calls the Gemini API to convert natural language text into 
    structured, quantifiable food items (JSON).
    """
    if not client:
        print("WARNING: Gemini Client not initialized. Cannot interpret meal.")
        return []

    try:
        prompt_with_meal = LLM_PROMPT.format(meal_description=meal_description)
        
        # Configure model to force JSON output
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "food_name": types.Schema(type=types.Type.STRING, description="The specific name of the food item."),
                        "quantity_g": types.Schema(type=types.Type.INTEGER, description="Estimated weight of the item in grams (g)."),
                    },
                    required=["food_name", "quantity_g"]
                )
            )
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_with_meal,
            config=config,
        )

        # The response.text will be a clean JSON string due to the configuration
        return json.loads(response.text)
    
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return []

def fetch_nutrient_data(food_name, quantity_g):
    """
    INTERNAL MOCK DB: This simulates fetching nutrient data from an internal
    database and scaling the nutrients by the consumed quantity.
    """
    # --- Mock Nutrient Data per 100g (simulating a database lookup) ---
    nutrients_100g = {}
    
    # Check for keywords from LLM output
    if 'bread' in food_name.lower() or 'toast' in food_name.lower():
        nutrients_100g = {'Calories': 260, 'Protein': 10, 'Iron': 1.5, 'Vitamin C': 0}
    elif 'turkey' in food_name.lower() or 'chicken' in food_name.lower():
        nutrients_100g = {'Calories': 110, 'Protein': 25, 'Iron': 1.0, 'Vitamin C': 0}
    elif 'oatmeal' in food_name.lower() or 'rice' in food_name.lower():
        nutrients_100g = {'Calories': 71, 'Protein': 2.5, 'Iron': 1.2, 'Vitamin C': 0}
    elif 'egg' in food_name.lower():
        nutrients_100g = {'Calories': 140, 'Protein': 12.5, 'Iron': 2.2, 'Vitamin C': 0}
    else:
        # Fallback for non-recognized items
        return pd.Series(dtype=float) 

    # Scale the nutrients based on the consumed quantity (quantity_g / 100)
    scaled_data = {
        k: (v * quantity_g / 100)
        for k, v in nutrients_100g.items()
    }
    scaled_data['Item'] = food_name
    scaled_data['Quantity'] = quantity_g
    
    # Return as a Pandas Series, matching the format expected by app.py
    return pd.Series(scaled_data)