import os
import sys
from google import genai
from google.genai import types

def generate_weekly_csv():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Find an active available Flash model from your account dynamically
    model_name = "gemini-2.5-flash"
    try:
        models = client.models.list()
        for m in models:
            if "flash" in m.name.lower() and "generateContent" in getattr(m, "supported_generation_methods", []):
                model_name = m.name
                break
        print(f"Using model: {model_name}")
    except Exception as e:
        print(f"Model list query failed, defaulting to {model_name}: {e}")

    prompt = """
    Provide the NASCAR Cup Series race results for the most recent completed race.
    Format the output strictly as a raw CSV block without markdown code fences or extra text.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )

        if not response or not response.text:
            print("Error: Empty response received from Gemini API.")
            sys.exit(1)

        # Clean markdown code formatting
        csv_text = response.text.strip()
        if csv_text.startswith("```"):
            csv_text = csv_text.split("\n", 1)[1]
        if csv_text.endswith("```"):
            csv_text = csv_text.rsplit("\n", 1)[0]
            
        csv_text = csv_text.replace("```csv", "").strip()

        with open("race_results.csv", "w", encoding="utf-8") as f:
            f.write(csv_text)
            
        print("race_results.csv created successfully!")

    except Exception as e:
        print(f"Error generating CSV from Gemini API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
