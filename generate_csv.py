import sys
import json
from curl_cffi import requests

def fetch_espn_json(url):
    """Fetches ESPN JSON using browser headers to ensure full payload delivery."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HTTP {response.status_code} for {url}")
    except Exception as e:
        print(f"Error fetching from ESPN: {e}")
    return None

def extract_stat_value(stats, possible_names):
    """Utility to pull specific numerical statistics by key aliases."""
    for stat in stats:
        name = stat.get("name", "")
        if name in possible_names:
            val = stat.get("displayValue") or stat.get("value") or 0
            try:
                return int(float(str(val)))
            except ValueError:
                return 0
    return 0

def extract_stat_float(stats, possible_names):
    """Utility to pull float values for lap times."""
    for stat in stats:
        name = stat.get("name", "")
        if name in possible_names:
            val = stat.get("value") or stat.get("displayValue") or 0
            try:
                return float(str(val))
            except ValueError:
                return 0.0
    return 0.0

def generate_weekly_csv():
    # 1. Fetch 2026 Cup Series Schedule
    sched_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"
    print("Fetching Cup Series event schedule...")
    sched_data = fetch_espn_json(sched_url)

    if not sched_data or "events" not in sched_data:
        print("Error: Could not retrieve schedule feed.")
        sys.exit(1)

    events = sched_data.get("events", [])
    completed_events = [
        e for e in events 
        if e.get("status", {}).get("type", {}).get("completed") is True or e.get("status", {}).get("type", {}).get("state") == "post"
    ]

    if not completed_events:
        # Fallback to the last listed event if state flag is omitted
        completed_events = events

    latest_event = completed_events[-1]
    event_id = latest_event.get("id")
    race_name = latest_event.get("name", "Unknown Race")
    print(f"Found latest completed race: {race_name} (ID: {event_id})")

    # 2. Fetch Detailed Race Summary
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/summary?event={event_id}"
    print("Fetching detailed race summary & statistics...")
    summary_data = fetch_espn_json(summary_url)

    competitors = []
    if summary_data:
        # Extract leaderboard competitors
        leaderboard = summary_data.get("leaderboard", {})
        competitors = leaderboard.get("competitors", [])

    if not competitors:
        # Fallback to scoreboard structure
        competitions = latest_event.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])

    if not competitors:
        print("Error: Driver leaderboard data unavailable.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # 3. Identify Fastest Lap Driver
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in competitors:
        stats = driver.get("statistics", [])
        lap_time = extract_stat_float(stats, ["fastestLapTime", "bestLapTime", "fastestLap"])
        if 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("id")

    # 4. Process Top 36 Drivers
    for driver in competitors[:36]:
        pos = driver.get("order") or driver.get("place") or driver.get("status", {}).get("position", "")
        
        athlete = driver.get("athlete", {})
        full_name = athlete.get("displayName", "")
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = athlete.get("firstName", full_name)
            last_name = athlete.get("lastName", "")

        stats = driver.get("statistics", [])
        
        # Parse points categories
        pts = extract_stat_value(stats, ["points", "pointsEarned", "totalPoints"])
        s1 = extract_stat_value(stats, ["stage1Points", "stage1", "s1Points"])
        s2 = extract_stat_value(stats, ["stage2Points", "stage2", "s2Points"])
        s3 = extract_stat_value(stats, ["stage3Points", "stage3", "s3Points"])

        # Fallback: calculate base points from finishing position if ESPN omits points stat
        if pts == 0 and pos:
            try:
                fin_pos = int(pos)
                if fin_pos == 1:
                    pts = 40  # 40 points for 1st place
                elif 2 <= fin_pos <= 35:
                    pts = 36 - (fin_pos - 2)  # 35 for 2nd down to 2 for 35th
                elif fin_pos >= 36:
                    pts = 1
            except ValueError:
                pts = 0

        # Binary flag for fastest lap (1 if driver set fastest lap, else 0)
        is_fastest_lap = 1 if driver.get("id") == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv updated successfully with statistics!")

if __name__ == "__main__":
    generate_weekly_csv()
