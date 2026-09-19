import sys
import json
import csv
from curl_cffi import requests

def fetch_nascar_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.nascar.com/",
        "Origin": "https://www.nascar.com"
    }
    try:
        res = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error requesting {url}: {e}")
    return None

def generate_weekly_csv():
    print("Fetching 2026 Cup Series schedule from NASCAR CDN...")
    
    # 1. Fetch official Cup Series (Series ID: 1) schedule
    sched_url = "https://cf.nascar.com/cacher/2026/1/schedule.json"
    sched_data = fetch_nascar_json(sched_url)

    if not sched_data:
        print("Error: Could not retrieve schedule feed.")
        sys.exit(1)

    races = sched_data if isinstance(sched_data, list) else sched_data.get("race_list", [])

    # Filter completed Cup Series events
    completed_races = [
        r for r in races 
        if isinstance(r, dict) and (r.get("results_posted") is True or r.get("race_status") in [2, 3])
    ]

    if not completed_races:
        print("Error: No completed 2026 Cup Series races found.")
        sys.exit(1)

    latest_race = completed_races[-1]
    race_id = latest_race.get("race_id")
    season = latest_race.get("season", 2026)

    print(f"Targeting Race: {latest_race.get('race_name')} (ID: {race_id})")

    # 2. Fetch full weekend feed containing official driver results & lap data
    weekend_url = f"https://cf.nascar.com/cacher/{season}/1/{race_id}/weekend-feed.json"
    data = fetch_nascar_json(weekend_url)

    if not data or "weekend_race" not in data:
        print("Error: Could not fetch weekend feed.")
        sys.exit(1)

    race_info = data["weekend_race"][0] if isinstance(data["weekend_race"], list) else data["weekend_race"]
    results = race_info.get("results", [])

    if not results:
        print("Error: No results found in weekend feed.")
        sys.exit(1)

    # Sort drivers strictly by finishing position
    results.sort(key=lambda x: int(x.get("finishing_position") or 999))

    # 3. Determine driver with fastest lap time
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in results:
        lap_time = driver.get("best_lap_time", 0) or driver.get("best_time", 0)
        try:
            lap_time = float(lap_time)
            if 0 < lap_time < best_lap_time:
                best_lap_time = lap_time
                fastest_lap_driver_id = driver.get("driver_id") or driver.get("finishing_position")
        except (ValueError, TypeError):
            continue

    # 4. Generate CSV Rows for top 36 drivers
    driver_rows = []
    for driver in results[:36]:
        pos = driver.get("finishing_position", "")

        first_name = driver.get("driver_first_name") or ""
        last_name = driver.get("driver_last_name") or ""

        if not first_name and not last_name:
            full_name = driver.get("driver_name", "")
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            else:
                first_name = full_name

        s1 = int(driver.get("stage_1_points", 0) or 0)
        s2 = int(driver.get("stage_2_points", 0) or 0)
        s3 = int(driver.get("stage_3_points", 0) or 0)
        pts = int(driver.get("points_earned", 0) or driver.get("points", 0) or 0)

        # Fallback to standard base point calculation if unpopulated
        if pts == 0 and pos:
            try:
                p_val = int(pos)
                base_pts = 40 if p_val == 1 else max(1, 36 - (p_val - 2))
                pts = base_pts + s1 + s2 + s3
            except ValueError:
                pts = 0

        driver_id = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_id == fastest_lap_driver_id else 0

        driver_rows.append([pos, first_name, last_name, pts, s1, s2, s3, is_fastest_lap])

    # Write output to CSV
    csv_headers = ["Position", "First_Name", "Last_Name", "Points", "Stage_1", "Stage_2", "Stage_3", "Fastest_Lap"]
    with open("race_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        writer.writerows(driver_rows)

    print("race_results.csv created with official Cup Series data, stage points, and fastest lap!")

if __name__ == "__main__":
    generate_weekly_csv()
