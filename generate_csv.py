import sys
import json
import urllib.request
import urllib.parse

# Your Cloudflare Worker URL
WORKER_URL = "https://fragrant-bonus-ba99.jsaxon2.workers.dev"

def fetch_via_worker(target_url):
    """Fetches NASCAR CDN feeds through your Cloudflare Worker pass-through."""
    encoded_url = urllib.parse.quote(target_url, safe='')
    proxy_request_url = f"{WORKER_URL}?url={encoded_url}"
    
    req = urllib.request.Request(proxy_request_url)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching {target_url} via Worker: {e}")
        return None

def generate_weekly_csv():
    # 1. Fetch 2026 Schedule Feed
    sched_url = "https://cf.nascar.com/cpm/prod/2026/1/schedule.json"
    print("Fetching 2026 schedule via Cloudflare Worker...")
    schedule_data = fetch_via_worker(sched_url)

    if not schedule_data:
        print("Error: Could not retrieve schedule feed.")
        sys.exit(1)

    races = schedule_data.get("race_list", schedule_data) if isinstance(schedule_data, dict) else schedule_data

    # Filter for completed races
    completed_races = [
        r for r in races 
        if isinstance(r, dict) and (r.get("results_posted") is True or r.get("race_status") == 3)
    ]

    if not completed_races:
        print("Error: No completed 2026 races found.")
        sys.exit(1)

    latest_race = completed_races[-1]
    race_id = latest_race["race_id"]
    season = latest_race.get("season", 2026)
    series_id = latest_race.get("series_id", 1)

    print(f"Found latest race: {latest_race.get('race_name', 'Unknown')} (ID: {race_id})")

    # 2. Fetch specific race results JSON
    results_url = f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json"
    results_data = fetch_via_worker(results_url)

    if not results_data:
        print("Error: Could not retrieve race results.")
        sys.exit(1)

    # 3. Parse driver rows into strict CSV format
    driver_rows = results_data.get("data", results_data) if isinstance(results_data, dict) else results_data
    if not isinstance(driver_rows, list):
        print("Error: Unexpected JSON structure in race results.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify fastest lap overall across drivers
    fastest_lap_driver_id = None
    best_lap_time = float('inf')
    for driver in driver_rows:
        lap_time = driver.get("best_lap_time", 0)
        if lap_time and 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("driver_id") or driver.get("finishing_position")

    for driver in driver_rows[:36]:  # Target full 36-driver field
        pos = driver.get("finishing_position") or driver.get("position", "")
        
        full_name = driver.get("driver_name", "")
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = driver.get("driver_first_name", "")
            last_name = driver.get("driver_last_name", "")

        pts = driver.get("points_earned", driver.get("points", 0))
        s1 = driver.get("stage_1_points", 0)
        s2 = driver.get("stage_2_points", 0)
        s3 = driver.get("stage_3_points", 0)

        # Flag 1 if driver set fastest lap, else 0
        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output to CSV
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
