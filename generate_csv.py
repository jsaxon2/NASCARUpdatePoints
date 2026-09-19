import sys
import json
from curl_cffi import requests

def fetch_nascar_json(url):
    """Fetches JSON payload using browser impersonation to bypass Cloudflare WAF."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nascar.com/",
        "Origin": "https://www.nascar.com"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.json()
        print(f"HTTP {response.status_code} for {url}")
    except Exception as e:
        print(f"Error requesting {url}: {e}")
    return None

def generate_weekly_csv():
    # 1. Retrieve 2026 Cup Series Schedule Feed
    print("Fetching 2026 NASCAR Cup Series schedule...")
    sched_url = "https://cf.nascar.com/cacher/2026/race_list_basic.json"
    sched_data = fetch_nascar_json(sched_url)

    if not sched_data:
        # Fallback to general schedule endpoint
        sched_url = "https://cf.nascar.com/cpm/prod/2026/1/schedule.json"
        sched_data = fetch_nascar_json(sched_url)

    if not sched_data:
        print("Error: Unable to fetch NASCAR schedule feed.")
        sys.exit(1)

    races = sched_data.get("race_list", sched_data) if isinstance(sched_data, dict) else sched_data

    # Filter for completed Cup Series (series_id 1) races
    completed_races = [
        r for r in races 
        if isinstance(r, dict) and r.get("series_id", 1) == 1 and (
            r.get("results_posted") is True or 
            r.get("race_status") in [2, 3] or 
            r.get("is_completed") is True
        )
    ]

    if not completed_races:
        print("Error: No completed 2026 Cup Series races found.")
        sys.exit(1)

    latest_race = completed_races[-1]
    race_id = latest_race.get("race_id")
    season = latest_race.get("season", 2026)
    series_id = latest_race.get("series_id", 1)

    print(f"Targeting Race: {latest_race.get('race_name', race_id)} (ID: {race_id})")

    # 2. Fetch Archived Weekend Feed containing stage breakdown & lap times
    weekend_url = f"https://cf.nascar.com/cacher/{season}/{series_id}/{race_id}/weekend-feed.json"
    print(f"Fetching archived weekend feed from {weekend_url}...")
    weekend_data = fetch_nascar_json(weekend_url)

    driver_rows = []
    if weekend_data and "weekend_race" in weekend_data:
        race_info = weekend_data.get("weekend_race", [{}])[0] if isinstance(weekend_data.get("weekend_race"), list) else weekend_data.get("weekend_race", {})
        driver_rows = race_info.get("results", [])

    # Secondary lookup fallback
    if not driver_rows:
        results_url = f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json"
        results_data = fetch_nascar_json(results_url)
        if results_data:
            driver_rows = results_data.get("data", results_data) if isinstance(results_data, dict) else results_data

    if not isinstance(driver_rows, list) or not driver_rows:
        print("Error: Could not retrieve valid driver result rows.")
        sys.exit(1)

    # Sort drivers by finishing position
    driver_rows.sort(key=lambda x: int(x.get("finishing_position") or x.get("position") or 999))

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # 3. Identify driver with fastest lap across race
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

    # 4. Process Top 36 Drivers
    for driver in driver_rows[:36]:
        pos = driver.get("finishing_position") or driver.get("position", "")

        driver_info = driver.get("driver", {})
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

        # Base finishing points calculation if points total is unpopulated
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

    # Write output CSV
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv generated successfully with stage points and fastest lap data!")

if __name__ == "__main__":
    generate_weekly_csv()
