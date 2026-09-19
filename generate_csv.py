import sys
import re
import csv
import requests
from bs4 import BeautifulSoup

def generate_weekly_csv():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    # 1. Fetch 2026 Cup Series Schedule to find the latest completed race URL
    schedule_url = "https://www.racing-reference.info/yeardet/2026/W"
    print(f"Fetching season schedule from {schedule_url}...")
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch schedule. HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"Connection error fetching schedule: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find links pointing to individual race results: race-results?series=W&raceId=2026-XX
    race_links = []
    for a in soup.find_all("a", href=True):
        if "race-results" in a["href"] and "series=W" in a["href"]:
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.racing-reference.info" + href
            race_links.append(href)

    if not race_links:
        print("Error: No completed 2026 Cup Series race result links found on schedule.")
        sys.exit(1)

    # Pick the most recent completed race link
    latest_race_url = race_links[-1]
    print(f"Targeting Latest Race: {latest_race_url}")

    # 2. Fetch the Race Results Page
    try:
        race_res = requests.get(latest_race_url, headers=headers, timeout=15)
        if race_res.status_code != 200:
            print(f"Failed to fetch race results. HTTP {race_res.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"Connection error fetching race page: {e}")
        sys.exit(1)

    race_soup = BeautifulSoup(race_res.text, "html.parser")
    
    # Locate table containing driver race results
    results_table = None
    for table in race_soup.find_all("table"):
        text = table.get_text()
        if "Driver" in text and ("Pts" in text or "Laps" in text or "Pos" in text):
            results_table = table
            break

    if not results_table:
        print("Error: Could not locate results table on race page.")
        sys.exit(1)

    rows = results_table.find_all("tr")
    driver_data = []

    # Parse headers to identify dynamic column indexes
    header_tr = rows[0]
    headers_text = [th.get_text().strip() for th in header_tr.find_all(["th", "td"])]
    
    pos_idx = 0
    driver_idx = 2
    pts_idx = -1

    for i, h in enumerate(headers_text):
        if h in ["Pos", "POS", "Fin"]:
            pos_idx = i
        elif h in ["Driver", "DRIVER"]:
            driver_idx = i
        elif h in ["Pts", "PTS", "Points"]:
            pts_idx = i

    # Parse Driver Data Rows
    for row in rows[1:]:
        cols = [td.get_text().strip() for td in row.find_all(["td", "th"])]
        if len(cols) <= max(pos_idx, driver_idx):
            continue

        pos_str = cols[pos_idx]
        if not pos_str.isdigit():
            continue

        pos = int(pos_str)
        full_name = cols[driver_idx]
        
        # Split first and last name cleanly
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name, last_name = full_name, ""

        pts = 0
        if pts_idx != -1 and pts_idx < len(cols):
            try:
                pts = int(re.sub(r"\D", "", cols[pts_idx]))
            except ValueError:
                pts = 0

        # Base NASCAR points calculation if unpopulated
        if pts == 0:
            pts = 40 if pos == 1 else max(1, 36 - (pos - 2))

        driver_data.append({
            "pos": pos,
            "first_name": first_name,
            "last_name": last_name,
            "pts": pts,
            "stage_1": 0,
            "stage_2": 0,
            "stage_3": 0,
            "fastest_lap": 0
        })

    if not driver_data:
        print("Error: No driver rows successfully parsed.")
        sys.exit(1)

    # Sort drivers by position
    driver_data.sort(key=lambda x: x["pos"])

    # 3. Write CSV Output
    csv_headers = ["Position", "First_Name", "Last_Name", "Points", "Stage_1", "Stage_2", "Stage_3", "Fastest_Lap"]
    
    with open("race_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for d in driver_data[:36]:
            writer.writerow([
                d["pos"],
                d["first_name"],
                d["last_name"],
                d["pts"],
                d["stage_1"],
                d["stage_2"],
                d["stage_3"],
                d["fastest_lap"]
            ])

    print("race_results.csv generated successfully from Racing-Reference!")

if __name__ == "__main__":
    generate_weekly_csv()
