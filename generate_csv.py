import os
import sys
import json
import urllib.request
from google import genai
from google.genai import types

def get_latest_race_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.nascar.com/',
        'Accept': 'application/json'
    }

    # 1. Fetch current live-feed or season schedule to resolve active race ID
    try:
        live_url = "https://cf.nascar.com/live/feeds/live-feed.json"
        req = urllib.request.Request(live_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            live_data = json.loads(response.read().decode())
            race_id = live_data.get("race_id")
            season = live_data.get("season")
            series_id = live_data.get("series_id", 1)

            if race_id and season:
                results_url = f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json"
                req_results = urllib.request.Request(results_url, headers=headers)
                with urllib.request.urlopen(req_results) as res_response:
                    data = json.loads(res_response.read().decode())
                    print(f"Successfully fetched race results for Race ID {race_id} ({season} Season).")
                    return data
    except Exception as e:
        print(f"Primary live feed fetch failed ({e}). Trying schedule index backup...")

    # 2. Backup: Fetch schedule index for current active race
    try:
        sched_url = "https://cf.nascar.com/cpm/prod/2026/1/race_list.json"
        req_sched = urllib.request.Request(sched_url, headers=headers)
        with urllib.request.urlopen(req_sched) as response:
            schedule = json.loads(response.read().decode())
            # Find the last completed race in the list
            completed_races = [r for r in schedule if r.get("race_status") == 3 or r.get("results_posted", False)]
            if completed_races:
                last_race = completed_races[-1]
                race_id = last_race["race_id"]
                season = last_race.get("season", 2026)
                series_id = last_race.get("series_id", 1)
                
                results_url = f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json"
                req_results = urllib.request.Request(results_url, headers=headers)
                with urllib.request.urlopen(req_results) as res_response:
                    print(f"Fetched backup schedule race results for Race ID {race_id}.")
                    return json.loads(res_response.read().decode())
    except Exception as e:
        print(f"Backup schedule fetch failed: {e}")

    return None

def generate_weekly_csv():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    raw_data = get_latest_race_data()
    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are a sports data processing assistant. Provide the NASCAR Cup Series race results for all 36 drivers in the most recent completed race provided in the payload.
    
    CRITICAL FORMAT REQUIREMENTS:
    - Output ONLY raw CSV text. Do not include markdown code blocks, ```csv, or conversational text.
    - Output all 36 drivers in finishing order (Position 1 through 36).
    - Do NOT include lap times or speeds.
    - Set Fastest_Lap to 1 if the driver had the fastest lap of the race, otherwise 0.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap

    Raw Data Payload:
    {json.dumps(raw_data) if raw_data else "Extract data for the most recently completed NASCAR Cup Series race."}
    """

    try:
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
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
