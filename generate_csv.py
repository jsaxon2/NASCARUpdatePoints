import sys
import json
from curl_cffi import requests

def fetch_nascar_json(url):
    """Fetches JSON using Chrome TLS impersonation to bypass Cloudflare 403 blocks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nascar.com/",
        "Origin": "https://www.nascar.com"
    }
    try:
        res = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if res.status_code == 200:
            return res.json()
        print(f"HTTP {res.status_code} for {url}")
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
    return None

def generate_weekly_csv():
    # 1. Fetch 2026 Cup Series schedule from primary CDN endpoints
    print("Fetching 2026 NASCAR Cup Series schedule...")
    
    endpoints = [
        "https://cf.nascar.com/cpm/prod/2026/1/schedule.json",
        "https://cf.nascar.com/cacher/2026/1/schedule.json",
        "https://cf.nascar.com/cacher/2026/race_list_basic.json"
    ]

    races = []
    for ep in endpoints:
        data = fetch_nascar_json(ep)
        if not data:
            continue
        
        if isinstance(data, list):
            races = data
            break
        elif isinstance(data, dict):
            races = data.get("race_list") or data.get("races") or data.get("events") or []
            if races:
                break

    if not races:
        print("Error: Could not retrieve schedule feed from any endpoint.")
        sys.exit(1)

    # Filter completed races safely regardless of data types
    completed_races = []
    for r in races:
        if not isinstance(r, dict):
            continue
        
        # Ensure Cup Series (series_id = 1)
        s_id = str(r.get("series_id", r.get("sub_series_id", 1)))
        if s_id != "1":
            continue

        # Check for completed flags (results_posted, race_status == 2 or 3, or is_completed)
        results_posted = r.get("results_posted") in [True, "true", "True", 1]
        status = str(r.get("race_status", r.get("status", "")))
        is_completed = r.get("is_completed") in [True, "true", 1]

        if results_posted or status in ["2", "3", "OFFICIAL", "COMPLETED"] or is_completed:
            completed_races.append(r)

    if not completed_races:
        print("No explicitly marked completed races found. Checking for races with valid race_ids...")
        # Fallback: Pick latest race that has a valid race_id and has already occurred
        completed_races = [r for r in races if isinstance(r, dict) and r.get("race_id")]

    if not completed_races:
        print("Error: No completed 2026 Cup Series races found.")
        sys.exit(1)

    latest_race = completed_races[-1]
    race_id = latest_race.get("race_id")
    season = latest_race.get("season", 2026)
    series_id = latest_race.get("series_id", 1)

    print(f"Targeting Race: {latest_race.get('race_name', race_id)} (ID: {race_id})")

    # 2. Fetch official race feed (weekend-feed or results.json)
    feed_urls = [
        f"https://cf.nascar.com/cacher/{season}/{series_id}/{race_id}/weekend-feed.json",
        f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json",
        f"https://cf.nascar.com/cacher/{season}/{series_id}/{race_id}/results.json"
    ]

    driver_rows = []
    for f_url in feed_urls:
        feed_data = fetch_nascar_json(f_url)
        if not feed_data:
            continue

        if "weekend_race" in feed_data:
            wr = feed_data.get("weekend_race")
            race_info = wr[0] if isinstance(wr, list) and len(wr) > 0 else wr
            driver_rows = race_info.get("results", []) if isinstance(race_info, dict) else []
        elif "data" in feed_data:
            driver_rows = feed_data.get("data", [])
        elif isinstance(feed_data, list):
            driver_rows = feed_data

        if driver_rows:
            break

    if not driver_rows:
        print("Error: Could not retrieve valid driver result rows from feed.")
        sys.exit(1)

    # Sort drivers by finishing position
    def safe_pos(d):
        val = d.get("finishing_position") or d.get("position") or 999
        try:
            return int(val)
        except (ValueError, TypeError):
            return 999

    driver_rows.sort(key=safe_pos)

    # 3. Identify Fastest Lap Driver
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in driver_rows:
        lap_time = driver.get("best_lap_time") or driver.get("fastest_lap_time") or driver.get("best_time") or 0
        try:
            lap_time = float(lap_time)
            if 0 < lap_time < best_lap_time:
                best_lap_time = lap_time
                fastest_lap_driver_id = driver.get("driver_id") or driver.get("finishing_position")
        except (ValueError, TypeError):
            continue

    # 4. Generate CSV Lines
    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    for driver in driver_rows[:36]:
        pos = driver.get("finishing_position") or driver.get("position", "")

        driver_info = driver.get("driver", {}) if isinstance(driver.get("driver"), dict) else {}
        first_name = driver_info.get("first_name") or driver.get("driver_first_name") or ""
        last_name = driver_info.get("last_name") or driver.get("driver_last_name") or ""

        if not first_name and not last_name:
            full_name = driver.get("driver_name") or driver_info.get("full_name") or ""
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            else:
                first_name = full_name

        s1 = int(driver.get("stage_1_points", 0) or driver.get("stage1_points", 0) or 0)
        s2 = int(driver.get("stage_2_points", 0) or driver.get("stage2_points", 0) or 0)
        s3 = int(driver.get("stage_3_points", 0) or driver.get("stage3_points", 0) or 0)

        pts = int(driver.get("points_earned", 0) or driver.get("points", 0) or 0)
        if pts == 0 and pos:
            try:
                p = int(pos)
                base_pts = 40 if p == 1 else max(1, 36 - (p - 2))
                pts = base_pts + s1 + s2 + s3
            except ValueError:
                pts = 0

        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv generated successfully with stage points and fastest lap data!")

if __name__ == "__main__":
    generate_weekly_csv()
