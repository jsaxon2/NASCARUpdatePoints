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

    prompt = """
    Provide the NASCAR Cup Series race results for the most recent completed race.
    Format the output strictly as a raw CSV block without markdown code fences or extra text.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    try:
        # Use gemini-3.6-flash as requested by the API error message
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )

        if not response or not response.text:
            print("Error: Empty response received from Gemini API.")
            sys.exit(1)

        # Clean markdown formatting if present
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
