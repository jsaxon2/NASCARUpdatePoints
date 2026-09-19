import sys
import json
import urllib.request

def fetch_json(url):
    """Fetches JSON standard library urllib without relying on blocked headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
    return None

def generate_weekly_csv():
    print("Fetching NASCAR Cup Series schedule from ESPN API...")
    
    # Primary Source: ESPN Public API for NASCAR Premier (Cup Series)
    espn_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"
    espn_data = fetch_json(espn_url)

    completed_events = []
    if espn_data and "events" in espn_data:
        for event in espn_data["events"]:
            status = event.get("status", {}).get("type", {}).get("completed", False)
            if status or event.get("status", {}).get("type", {}).get("name") == "STATUS_FINAL":
                completed_events.append(event)

    if not completed_events:
        print("Warning: No completed events returned by live ESPN feed. Checking calendar history...")
        # Historical date range lookup fallback
        calendar_url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard?dates=20260201-20261130"
        espn_data = fetch_json(calendar_url)
        if espn_data and "events" in espn_data:
            for event in espn_data["events"]:
                status = event.get("status", {}).get("type", {}).get("completed", False)
                if status or event.get("status", {}).get("type", {}).get("name") == "STATUS_FINAL":
                    completed_events.append(event)

    if not completed_events:
        print("Error: Could not retrieve any completed 2026 Cup Series events.")
        sys.exit(1)

    # Grab the most recent completed race
    latest_event = completed_events[-1]
    race_name = latest_event.get("name", "Unknown Race")
    print(f"Targeting Race: {race_name}")

    competition = latest_event.get("competitions", [{}])[0]
    competitors = competition.get("competitors", [])

    if not competitors:
        print("Error: No competitor data found for the target event.")
        sys.exit(1)

    # Sort competitors by finishing order
    competitors.sort(key=lambda x: int(x.get("order") or x.get("winner", False) or 999))

    csv_lines = ["Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap"]

    # Process Top 36 Drivers
    for comp in competitors[:36]:
        pos = comp.get("order") or comp.get("place") or ""
        athlete = comp.get("athlete", {})
        
        first_name = athlete.get("firstName") or athlete.get("shortName", "")
        last_name = athlete.get("lastName") or athlete.get("displayName", "")
        
        if not first_name and not last_name:
            full_name = athlete.get("displayName") or comp.get("athlete", {}).get("name", "")
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            else:
                first_name = full_name

        # Parse stage breakdown and points linescores if present
        s1, s2, s3 = 0, 0, 0
        linescores = comp.get("linescores", [])
        for ls in linescores:
            period = ls.get("period")
            val = int(ls.get("value", 0))
            if period == 1:
                s1 = val
            elif period == 2:
                s2 = val
            elif period == 3:
                s3 = val

        # Total points earned
        pts = int(comp.get("score", 0) or comp.get("points", 0) or 0)
        
        # Calculate standard NASCAR base points if individual race points were omitted
        if pts == 0 and pos:
            try:
                p = int(pos)
                base_pts = 40 if p == 1 else max(1, 36 - (p - 2))
                pts = base_pts + s1 + s2 + s3
            except ValueError:
                pts = 0

        # Check for fastest lap status flag in athlete statistics/records
        is_fastest_lap = 1 if comp.get("fastestLap") is True or comp.get("records", [{}])[0].get("name") == "fastestLap" else 0

        csv_lines.append(f"{pos},{first_name},{last_name},{pts},{s1},{s2},{s3},{is_fastest_lap}")

    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))

    print("race_results.csv generated successfully using ESPN API!")

if __name__ == "__main__":
    generate_weekly_csv()
