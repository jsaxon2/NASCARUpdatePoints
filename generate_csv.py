import sys
import json
from curl_cffi import requests

def fetch_nascar_live_json(url):
    """
    Fetches public live feed JSON from m.nascar.com which bypasses 
    the cpm/prod CDN 403 blocks.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nascar.com/"
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HTTP {response.status_code} for {url}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

    return None

def generate_weekly_csv():
    # 1. Fetch live weekend feed index
    print("Fetching live race feed index...")
    live_feed_url = "https://m.nascar.com/live/feeds/live-feed.json"
    live_data = fetch_nascar_live_json(live_feed_url)

    # Fallback to current points feed if live-feed is off-air
    if not live_data or "driver" not in live_data:
        print("Live feed off-air or unavailable. Fetching Cup Series standings feed...")
        live_feed_url = "https://m.nascar.com/live/feeds/points/1.json"
        live_data = fetch_nascar_live_json(live_feed_url)

    if not live_data:
        print("Error: Could not retrieve NASCAR live or points feed.")
        sys.exit(1)

    # 2. Extract driver rows
    driver_rows = live_data.get("driver", []) or live_data.get("data", [])
    if not driver_rows and isinstance(live_data, list):
        driver_rows = live_data

    if not isinstance(driver_rows, list) or not driver_rows:
        print("Error: Empty driver list returned from feed.")
        sys.exit(1)

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Determine driver with fastest lap overall
    fastest_lap_driver_id = None
    best_lap_time = float('inf')
    for driver in driver_rows:
        lap_time = float(driver.get("best_lap_time", 0) or driver.get("best_time", 0) or 0)
        if lap_time > 0 and lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("driver_id") or driver.get("position")

    # Format target 36-driver field
    for driver in driver_rows[:36]:
        pos = driver.get("position") or driver.get("finishing_position") or ""
        
        full_name = driver.get("driver_name") or driver.get("name") or ""
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = driver.get("first_name", full_name)
            last_name = driver.get("last_name", "")

        pts = int(driver.get("points") or driver.get("points_earned") or 0)
        s1 = int(driver.get("stage_1_points") or driver.get("s1_points") or 0)
        s2 = int(driver.get("stage_2_points") or driver.get("s2_points") or 0)
        s3 = int(driver.get("stage_3_points") or driver.get("s3_points") or 0)

        # Binary flag for fastest lap
        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output to CSV
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
