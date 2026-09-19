import sys
import json
import urllib.request

def fetch_espn_json(url):
    """Fetches public ESPN racing feed without Cloudflare restrictions."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching from ESPN API: {e}")
        return None

def generate_weekly_csv():
    # 1. Fetch 2026 Cup Series Schedule from ESPN
    sched_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar/scoreboard?dates=2026"
    print("Fetching 2026 Cup Series schedule from ESPN API...")
    sched_data = fetch_espn_json(sched_url)

    if not sched_data or "events" not in sched_data:
        print("Error: Could not retrieve schedule feed.")
        sys.exit(1)

    events = sched_data.get("events", [])
    
    # Filter for completed events
    completed_events = [
        e for e in events 
        if e.get("status", {}).get("type", {}).get("completed") is True
    ]

    if not completed_events:
        print("Error: No completed 2026 Cup Series races found.")
        sys.exit(1)

    latest_event = completed_events[-1]
    event_id = latest_event["id"]
    event_name = latest_event.get("name", "Unknown Race")
    print(f"Found latest completed race: {event_name} (ID: {event_id})")

    # 2. Fetch detailed event summary
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/racing/nascar/summary?event={event_id}"
    summary_data = fetch_espn_json(summary_url)

    if not summary_data:
        print("Error: Could not retrieve race summary details.")
        sys.exit(1)

    competitors = summary_data.get("leaderboard", {}).get("competitors", [])
    if not competitors:
        # Fallback to event context structure
        competitions = latest_event.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])

    if not competitors:
        print("Error: Driver leaderboard structure empty.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify overall fastest lap across drivers
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in competitors:
        stats = {s.get("name"): s.get("value") for s in driver.get("statistics", [])}
        lap_time = float(stats.get("fastestLapTime", 0) or 0)
        if lap_time > 0 and lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("id")

    # Format 36 drivers
    for driver in competitors[:36]:
        pos = driver.get("order") or driver.get("status", {}).get("position", "")
        
        athlete = driver.get("athlete", {})
        first_name = athlete.get("firstName", "")
        last_name = athlete.get("lastName", "")
        
        if not first_name and not last_name:
            full_name = athlete.get("displayName", "")
            first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")

        stats = {s.get("name"): s.get("value", 0) for s in driver.get("statistics", [])}
        
        pts = int(stats.get("points", 0) or 0)
        s1 = int(stats.get("stage1Points", 0) or 0)
        s2 = int(stats.get("stage2Points", 0) or 0)
        s3 = int(stats.get("stage3Points", 0) or 0)

        # Flag 1 if driver had fastest lap, else 0
        is_fastest_lap = 1 if driver.get("id") == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output to CSV
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
