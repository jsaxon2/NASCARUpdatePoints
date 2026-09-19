import sys
import json
from curl_cffi import requests

def fetch_nascar_json(url):
    """Fetches JSON from NASCAR's public feeds using Chrome impersonation."""
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
        else:
            print(f"HTTP {response.status_code} for {url}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def generate_weekly_csv():
    # 1. Fetch live or points feed from NASCAR m.nascar.com edge CDN
    print("Fetching race feed from NASCAR public feeds...")
    live_feed_url = "https://m.nascar.com/live/feeds/live-feed.json"
    data = fetch_nascar_json(live_feed_url)

    # Fallback to Cup points feed if live-feed is off-air
    if not data or "driver" not in data:
        print("Live feed inactive, checking Cup Series points feed...")
        live_feed_url = "https://m.nascar.com/live/feeds/points/1.json"
        data = fetch_nascar_json(live_feed_url)

    # Secondary fallback to ESPN for base finishing order if NASCAR CDN is completely unreachable
    if not data:
        print("Falling back to ESPN API for race standings...")
        espn_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"
        espn_data = fetch_nascar_json(espn_url)
        if not espn_data or "events" not in espn_data:
            print("Error: Could not retrieve data from any source.")
            sys.exit(1)
        
        events = espn_data.get("events", [])
        latest_event = events[-1] if events else {}
        competitors = latest_event.get("competitions", [{}])[0].get("competitors", [])

        csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]
        for comp in competitors[:36]:
            pos = comp.get("order") or comp.get("place") or ""
            athlete = comp.get("athlete", {})
            full_name = athlete.get("displayName", "")
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            else:
                first_name = athlete.get("firstName", full_name)
                last_name = athlete.get("lastName", "")
            
            # Base Cup Series points calculation rule
            try:
                p = int(pos)
                pts = 55 if p == 1 else max(1, 36 - (p - 2))
            except ValueError:
                pts = 0

            csv_lines.append(f"{pos},{first_name},{last_name},{pts},0,0,0,0")

        with open("race_results.csv", "w", encoding="utf-8") as f:
            f.write("\n".join(csv_lines))
        print("race_results.csv created with base standings.")
        return

    # Process driver rows from NASCAR JSON feed
    driver_rows = data.get("driver", []) or data.get("data", [])
    if not isinstance(driver_rows, list):
        driver_rows = []

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify overall fastest lap
    fastest_lap_driver_id = None
    best_lap_time = float("inf")

    for driver in driver_rows:
        lap_time = float(driver.get("best_lap_time", 0) or driver.get("best_time", 0) or 0)
        if 0 < lap_time < best_lap_time:
            best_lap_time = lap_time
            fastest_lap_driver_id = driver.get("driver_id") or driver.get("position")

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

        driver_identifier = driver.get("driver_id") or pos
        is_fastest_lap = 1 if driver_identifier == fastest_lap_driver_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv generated successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
