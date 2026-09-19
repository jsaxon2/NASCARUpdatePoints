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

    # 1. Fetch latest race JSON directly with browser headers to prevent HTTP 403
    json_url = "https://cf.nascar.com/cpm/prod/2026/1/5412/results.json"
    raw_data = None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.nascar.com/',
        'Accept': 'application/json'
    }

    try:
        req = urllib.request.Request(json_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            raw_data = json.loads(response.read().decode())
            print("Successfully fetched live NASCAR JSON feed.")
    except Exception as e:
        print(f"Warning: Could not fetch live feed directly ({e}). Prompting Gemini directly.")

    # 2. Initialize Client
    client = genai.Client(api_key=api_key)

    # 3. Build prompt
    prompt = f"""
    You are a sports data processing assistant. Provide the NASCAR Cup Series race results for all 36 drivers in the most recent race.
    
    CRITICAL FORMAT REQUIREMENTS:
    - Output ONLY raw CSV text. Do not include markdown code blocks, ```csv, or conversational text.
    - Output all 36 drivers in finishing order (Position 1 through 36).
    - Do NOT include lap times or speeds.
    - Set Fastest_Lap to 1 if the driver had the fastest lap of the race, otherwise 0.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap

    Raw Data:
    {json.dumps(raw_data) if raw_data else "Extract data for the most recent NASCAR Cup Series race."}
    """

    try:
        # Changed model to gemini-3.6-flash as required by API response
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0
            )
        )

        if not response or not response.text:
            print("Error: Empty response received from Gemini API.")
            sys.exit(1)

        # Clean markdown wrappers if returned
        csv_text = response.text.strip()
        if csv_text.startswith("```"):
            csv_text = csv_text.split("\n", 1)[1]
        if csv_text.endswith("```"):
            csv_text = csv_text.rsplit("\n", 1)[0]
        csv_text = csv_text.replace("```csv", "").strip()

        with open("race_results.csv", "w", encoding="utf-8") as f:
            f.write(csv_text)
            
        print("race_results.csv generated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
