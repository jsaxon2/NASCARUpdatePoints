import os
import sys
from google import genai
from google.genai import types

def generate_weekly_csv():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = """
    Search the web for the official results of the most recent NASCAR Cup Series race.
    Generate a full 36-driver CSV list for all drivers who competed in finishing order (Position 1 through 36).
    
    CRITICAL FORMAT REQUIREMENTS:
    - Output ONLY raw CSV text with no markdown code blocks (no ``` or ```csv) or conversational text.
    - Do NOT include lap times or speeds.
    - Set Fastest_Lap to 1 if the driver set the fastest lap of the race, otherwise 0.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    try:
        # Enable Google Search Grounding tool
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                tools=[{"google_search": {}}]  # Allows Gemini to search the web live
            )
        )

        if not response or not response.text:
            print("Error: Empty response received from Gemini API.")
            sys.exit(1)

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
        print(f"Error generating CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
