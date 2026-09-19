import sys
import json
from playwright.sync_api import sync_playwright

def fetch_json_with_playwright(url):
    """Uses Playwright to bypass Cloudflare anti-bot checks and fetch JSON."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create a browser context with desktop User-Agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        if not response or response.status != 200:
            print(f"Failed to load {url} (Status: {response.status if response else 'No Response'})")
            browser.close()
            return None

        content = page.locator("body").inner_text()
        browser.close()
        return json.loads(content)

def get_latest_race_csv():
    try:
        # 1. Fetch 2026 Cup Series Schedule
        sched_url = "https://cf.nascar.com/cpm/prod/2026/1/schedule.json"
        print("Fetching schedule via Playwright...")
        schedule_data = fetch_json_with_playwright(sched_url)

        if not schedule_data:
            print("Error: Could not retrieve schedule data.")
            sys.exit(1)

        races = schedule_data.get("race_list", schedule_data) if isinstance(schedule_data, dict) else schedule_data

        # Filter completed races
        completed_races = [
            r for r in races 
            if isinstance(r, dict) and (r.get("results_posted") is True or r.get("race_status") == 3)
        ]

        if not completed_races:
            print("Error: No completed 2026 races found in schedule feed.")
            sys.exit(1)

        latest_race = completed_races[-1]
        race_id = latest_race["race_id"]
        season = latest_race.get("season", 2026)
        series_id = latest_race.get("series_id", 1)

        print(f"Found 2026 Race ID: {race_id} ({latest_race.get('race_name')})")

        # 2. Fetch specific race results JSON
        results_url = f"https://cf.nascar.com/cpm/prod/{season}/{series_id}/{race_id}/results.json"
        results_data = fetch_json_with_playwright(results_url)

        if not results_data:
            print("Error: Could not retrieve race results data.")
            sys.exit(1)

    except Exception as e:
        print(f"Error executing Playwright script: {e}")
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

        # Output 1 if driver had fastest lap, else 0
        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    # Write output to CSV
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    get_latest_race_csv()
