import sys
import json
import urllib.parse
from curl_cffi import requests

def fetch_nascar_json_via_proxy(endpoint_path):
    """
    Routes NASCAR CDN requests through an edge proxy to bypass 
    GitHub Actions datacenter IP blocks, while maintaining real browser headers.
    """
    target_url = f"https://cf.nascar.com/cpm/prod/{endpoint_path}"
    encoded_url = urllib.parse.quote(target_url, safe='')
    
    # Primary and fallback proxies
    proxy_urls = [
        f"https://corsproxy.io/?{encoded_url}",
        f"https://api.allorigins.win/raw?url={encoded_url}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nascar.com/"
    }

    for proxy_url in proxy_urls:
        try:
            response = requests.get(proxy_url, headers=headers, impersonate="chrome120", timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Proxy HTTP {response.status_code} for {proxy_url}")
        except Exception as e:
            print(f"Error fetching via proxy: {e}")

    return None

def generate_weekly_csv():
    print("Fetching 2026 schedule feed via edge proxy...")
    schedule_data = fetch_nascar_json_via_proxy("2026/1/schedule.json")

    if not schedule_data:
        print("Error: Could not retrieve schedule feed.")
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

    # Fetch race results JSON
    results_endpoint = f"{season}/{series_id}/{race_id}/results.json"
    results_data = fetch_nascar_json_via_proxy(results_endpoint)

    if not results_data:
        print("Error: Could not retrieve race results.")
        sys.exit(1)

    driver_rows = results_data.get("data", results_data) if isinstance(results_data, dict) else results_data
    if not isinstance(driver_rows, list):
        print("Error: Unexpected JSON structure in race results.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify driver with overall fastest lap
    fastest_lap_driver_id = None
    best_lap_time = float('inf')
    for driver in driver_rows:
        lap_time = driver.get("best_lap_time", 0)
        if lap_time and 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("driver_id") or driver.get("finishing_position")

    # Target 36 drivers
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

        # Flag 1 if driver had fastest lap, else 0
        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
