import sys
import json
from curl_cffi import requests

def fetch_nascar_json(endpoint_path):
    """
    Fetches JSON feeds directly from NASCAR's CDN by spoofing Chrome's TLS fingerprint (JA3/JA4).
    This bypasses Cloudflare WAF restrictions completely without proxies.
    """
    # Primary URL and Backup Cacher URL
    urls = [
        f"https://cf.nascar.com/cpm/prod/{endpoint_path}",
        f"https://cf.nascar.com/cacher/{endpoint_path}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nascar.com/",
        "Origin": "https://www.nascar.com"
    }

    for url in urls:
        try:
            # impersonate="chrome120" mimics a real desktop browser TLS client
            response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HTTP {response.status_code} for {url}")
        except Exception as e:
            print(f"Error requesting {url}: {e}")

    return None

def generate_weekly_csv():
    # 1. Fetch 2026 Cup Series Schedule Feed
    print("Fetching 2026 schedule feed via TLS impersonation...")
    schedule_data = fetch_nascar_json("2026/1/schedule.json")

    if not schedule_data:
        print("Error: Could not retrieve schedule feed from NASCAR CDN.")
        sys.exit(1)

    races = schedule_data.get("race_list", schedule_data) if isinstance(schedule_data, dict) else schedule_data

    # Filter completed races
    completed_races = [
        r for r in races 
        if isinstance(r, dict) and (r.get("results_posted") is True or r.get("race_status") == 3)
    ]

    if not completed_races:
        print("Error: No completed 2026 Cup Series races found in feed.")
        sys.exit(1)

    latest_race = completed_races[-1]
    race_id = latest_race["race_id"]
    season = latest_race.get("season", 2026)
    series_id = latest_race.get("series_id", 1)

    print(f"Found latest completed race: {latest_race.get('race_name', 'Unknown')} (ID: {race_id})")

    # 2. Fetch specific race results JSON
    results_endpoint = f"{season}/{series_id}/{race_id}/results.json"
    results_data = fetch_nascar_json(results_endpoint)

    if not results_data:
        print("Error: Could not retrieve race results.")
        sys.exit(1)

    # 3. Parse driver rows into strict CSV format
    driver_rows = results_data.get("data", results_data) if isinstance(results_data, dict) else results_data
    if not isinstance(driver_rows, list):
        print("Error: Unexpected JSON structure in race results.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify driver with fastest lap overall (lowest lap time)
    fastest_lap_driver_id = None
    best_lap_time = float('inf')
    for driver in driver_rows:
        lap_time = driver.get("best_lap_time", 0)
        if lap_time and 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("driver_id") or driver.get("finishing_position")

    # Target full 36-driver field
    for driver in driver_rows[:36]:
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

        # Binary 1 or 0 flag for fastest lap
        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output file
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully with current 2026 data!")

if __name__ == "__main__":
    generate_weekly_csv()
