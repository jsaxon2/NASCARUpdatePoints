import sys
import json
import csv
from curl_cffi import requests

def generate_weekly_csv():
    session = requests.Session(impersonate="chrome120")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.espn.com/",
        "Origin": "https://www.espn.com"
    }

    print("Fetching 2026 NASCAR Cup Series schedule from ESPN API...")
    
    # Query full schedule endpoint for 2026 season
    schedule_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard?dates=2026"
    
    data = None
    try:
        res = session.get(schedule_url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
        else:
            print(f"Schedule endpoint returned HTTP {res.status_code}")
    except Exception as e:
        print(f"Error fetching schedule: {e}")

    if not data or "events" not in data:
        print("Error: Unable to retrieve schedule or event list from ESPN API.")
        sys.exit(1)

    completed_events = []
    for event in data.get("events", []):
        status_info = event.get("status", {}).get("type", {})
        is_completed = status_info.get("completed") is True or status_info.get("name") in ["STATUS_FINAL", "STATUS_COMPLETED"]
        
        # Ensure event has competition results available
        competitions = event.get("competitions", [])
        has_competitors = len(competitions) > 0 and len(competitions[0].get("competitors", [])) > 0
        
        if is_completed or has_competitors:
            completed_events.append(event)

    if not completed_events:
        print("Error: No completed 2026 Cup Series events found in feed.")
        sys.exit(1)

    # Pick the most recently completed race
    latest_event = completed_events[-1]
    race_name = latest_event.get("name", "NASCAR Cup Race")
    print(f"Targeting Latest Race: {race_name}")

    competitions = latest_event.get("competitions", [{}])
    competitors = competitions[0].get("competitors", []) if competitions else []

    if not competitors:
        print("Error: No driver entry records found in target event.")
        sys.exit(1)

    def safe_order(c):
        try:
            return int(c.get("order") or c.get("place") or 999)
        except (ValueError, TypeError):
            return 999

    competitors.sort(key=safe_order)

    driver_rows = []
    for comp in competitors[:36]:
        pos = comp.get("order") or comp.get("place") or ""
        athlete = comp.get("athlete", {}) if isinstance(comp.get("athlete"), dict) else {}

        first_name = athlete.get("firstName") or athlete.get("shortName", "")
        last_name = athlete.get("lastName") or athlete.get("displayName", "")

        if not first_name and not last_name:
            full_name = athlete.get("displayName") or comp.get("name", "")
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            else:
                first_name = full_name

        s1, s2, s3 = 0, 0, 0
        linescores = comp.get("linescores", [])
        for ls in linescores:
            p = ls.get("period")
            val = int(ls.get("value", 0))
            if p == 1:
                s1 = val
            elif p == 2:
                s2 = val
            elif p == 3:
                s3 = val

        pts = int(comp.get("score", 0) or comp.get("points", 0) or 0)
        if pts == 0 and pos:
            try:
                p_val = int(pos)
                base_pts = 40 if p_val == 1 else max(1, 36 - (p_val - 2))
                pts = base_pts + s1 + s2 + s3
            except ValueError:
                pts = 0

        is_fastest_lap = 1 if comp.get("fastestLap") is True else 0

        driver_rows.append([pos, first_name, last_name, pts, s1, s2, s3, is_fastest_lap])

    csv_headers = ["Position", "First_Name", "Last_Name", "Points", "Stage_1", "Stage_2", "Stage_3", "Fastest_Lap"]
    with open("race_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        writer.writerows(driver_rows)

    print("race_results.csv generated successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
