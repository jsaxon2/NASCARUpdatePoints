import sys
import json
from curl_cffi import requests

def fetch_espn_nascar_data():
    """
    Fetches completed NASCAR Cup Series events and race results 
    from ESPN's public API, which does not block GitHub Actions IPs.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"ESPN API HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching ESPN data: {e}")

    return None

def generate_weekly_csv():
    print("Fetching latest NASCAR Cup Series data from ESPN API...")
    data = fetch_espn_nascar_data()

    if not data or "events" not in data:
        print("Error: Could not retrieve events from ESPN feed.")
        sys.exit(1)

    events = data.get("events", [])
    if not events:
        print("Error: No events found in feed.")
        sys.exit(1)

    # Find the most recent event with available results/competitors
    latest_event = None
    competitors = []

    for event in reversed(events):
        competitions = event.get("competitions", [])
        if competitions:
            comp = competitions[0]
            comps = comp.get("competitors", [])
            if comps:
                latest_event = event
                competitors = comps
                break

    if not latest_event or not competitors:
        print("Error: No race competitors/results found in recent events.")
        sys.exit(1)

    race_name = latest_event.get("name", "NASCAR Race")
    print(f"Found latest race: {race_name}")

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Identify athlete with fastest lap flag if present in statistics
    fastest_lap_athlete_id = None
    best_lap_time = float('inf')

    for comp in competitors:
        stats = comp.get("statistics", [])
        for stat in stats:
            if stat.get("name") in ["fastestLapTime", "bestLapTime"]:
                try:
                    val = float(stat.get("value", 0))
                    if 0 < val < best_lap_time:
                        best_lap_time = val
                        fastest_lap_athlete_id = comp.get("id")
                except ValueError:
                    pass

    # Process top 36 drivers
    for comp in competitors[:36]:
        pos = comp.get("order") or comp.get("place") or ""
        
        athlete = comp.get("athlete", {})
        full_name = athlete.get("displayName", "")
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = athlete.get("firstName", full_name)
            last_name = athlete.get("lastName", "")

        # Extract points and stage details from statistics array
        pts = 0
        s1 = 0
        s2 = 0
        s3 = 0

        for stat in comp.get("statistics", []):
            name = stat.get("name", "")
            val = stat.get("displayValue") or stat.get("value") or "0"
            try:
                num_val = int(float(str(val)))
                if name in ["points", "pointsEarned"]:
                    pts = num_val
                elif name == "stage1Points":
                    s1 = num_val
                elif name == "stage2Points":
                    s2 = num_val
                elif name == "stage3Points":
                    s3 = num_val
            except ValueError:
                pass

        # If points aren't explicitly listed in stats, extract from linescores/summary
        if pts == 0 and "score" in comp:
            try:
                pts = int(float(comp.get("score", 0)))
            except ValueError:
                pts = 0

        # Binary flag (1 if fastest lap, else 0)
        is_fastest_lap = 1 if comp.get("id") == fastest_lap_athlete_id else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
