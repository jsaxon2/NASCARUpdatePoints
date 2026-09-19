import sys
import json
from curl_cffi import requests

def fetch_espn_json(url):
    """Fetches JSON payload from ESPN's API using Chrome browser impersonation."""
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

def extract_stat_value(stats_list, target_names):
    """Parses integer stat values (like stage points or total points) from ESPN statistics arrays."""
    for stat in stats_list:
        if stat.get("name") in target_names:
            val = stat.get("displayValue") or stat.get("value") or "0"
            try:
                return int(float(str(val)))
            except ValueError:
                return 0
    return 0

def extract_stat_float(stats_list, target_names):
    """Parses float stat values (like fastest lap times) from ESPN statistics arrays."""
    for stat in stats_list:
        if stat.get("name") in target_names:
            val = stat.get("value") or stat.get("displayValue") or "0"
            try:
                return float(str(val))
            except ValueError:
                return 0.0
    return 0.0

def generate_weekly_csv():
    # 1. Fetch 2026 Cup Series Schedule to locate the latest race ID
    sched_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard?dates=2026"
    print("Fetching 2026 Cup Series schedule from ESPN...")
    sched_data = fetch_espn_json(sched_url)

    if not sched_data or "events" not in sched_data:
        print("Error: Could not retrieve schedule feed from ESPN API.")
        sys.exit(1)

    events = sched_data.get("events", [])
    
    # Filter for completed events
    completed_events = [
        e for e in events 
        if e.get("status", {}).get("type", {}).get("completed") is True 
        or e.get("status", {}).get("type", {}).get("state") == "post"
    ]

    if not completed_events:
        print("Error: No completed 2026 Cup Series races found in feed.")
        sys.exit(1)

    latest_event = completed_events[-1]
    event_id = latest_event.get("id")
    race_name = latest_event.get("name", "Unknown Race")
    print(f"Found latest completed race: {race_name} (ID: {event_id})")

    # 2. Fetch Detailed Race Summary Endpoint for Statistics
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/summary?event={event_id}"
    print(f"Fetching detailed race statistics for event {event_id}...")
    summary_data = fetch_espn_json(summary_url)

    competitors = []
    if summary_data:
        leaderboard = summary_data.get("leaderboard", {})
        competitors = leaderboard.get("competitors", [])

    # Fallback to schedule competitors if summary leaderboard is structured differently
    if not competitors:
        competitions = latest_event.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])

    if not competitors:
        print("Error: Empty competitor array returned from race summary.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # 3. Identify overall fastest lap driver across the field
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in competitors:
        stats = driver.get("statistics", [])
        lap_time = extract_stat_float(stats, ["fastestLapTime", "bestLapTime", "fastestLap"])
        if 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("id")

    # 4. Format the top 36 drivers into CSV
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
        
        # Extract numerical statistics
        pts = extract_stat_value(stats, ["points", "pointsEarned", "totalPoints"])
        s1 = extract_stat_value(stats, ["stage1Points", "stage1", "s1Points"])
        s2 = extract_stat_value(stats, ["stage2Points", "stage2", "s2Points"])
        s3 = extract_stat_value(stats, ["stage3Points", "stage3", "s3Points"])

        # Base finishing points fallback if total points stat is omitted by feed
        if pts == 0 and pos:
            try:
                fin_pos = int(pos)
                if fin_pos == 1:
                    pts = 40
                elif 2 <= fin_pos <= 35:
                    pts = 36 - (fin_pos - 2)
                elif fin_pos >= 36:
                    pts = 1
            except ValueError:
                pts = 0

        # Binary flag: 1 if driver recorded overall fastest lap, else 0
        is_fastest_lap = 1 if driver.get("id") == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output file
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv updated successfully with full race points!")

if __name__ == "__main__":
    generate_weekly_csv()
