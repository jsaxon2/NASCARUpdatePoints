import os
import sys
import json
import urllib.request
from google import genai
from google.genai import types

def generate_weekly_csv():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    # 1. Fetch latest race JSON directly from NASCAR's CDN
    # Example feed endpoint for current race results
    json_url = "https://cf.nascar.com/cpm/prod/2026/1/5412/results.json"
    
    try:
        req = urllib.request.Request(
            json_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            raw_data = json.loads(response.read().decode())
            print("Successfully fetched live race JSON.")
    except Exception as e:
        print(f"Warning: Could not fetch live feed directly ({e}). Prompting Gemini directly.")
        raw_data = None

    # 2. Initialize Gemini Client
    client = genai.Client(api_key=api_key)

    # 3. Construct prompt with explicit guidelines and raw data if available
    prompt = f"""
    You are a data conversion assistant. Generate a complete 36-driver CSV for the most recent NASCAR Cup Series race.
    
    CRITICAL INSTRUCTIONS:
    - Include ALL 36 drivers who finished the race.
    - Do NOT include lap times or speeds.
    - Points calculation: Fastest_Lap should be 1 if the driver had the fastest lap of the race, otherwise 0.
    - Output strictly raw CSV text with no markdown fences, explanations, or commentary.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    
    Raw Race Data:
    {json.dumps(raw_data) if raw_data else "Fetch the most recent NASCAR Cup Series race results."}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0
            )
        )

        if not response or not response.text:
            print("Error: Empty response from Gemini API.")
            sys.exit(1)

        # Clean markdown code block markers
        csv_text = response.text.strip()
        if csv_text.startswith("```"):
            csv_text = csv_text.split("\n", 1)[1]
        if csv_text.endswith("```"):
            csv_text = csv_text.rsplit("\n", 1)[0]
        csv_text = csv_text.replace("```csv", "").strip()

        # Save to file
        with open("race_results.csv", "w", encoding="utf-8") as f:
            f.write(csv_text)
            
        print("race_results.csv generated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
