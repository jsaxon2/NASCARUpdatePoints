#!/usr/bin/env python3
"""
NASCAR Cup Series Results → custom CSV format
Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap

Fastest_Lap = 1 for the driver who set the overall fastest lap, 0 for everyone else
"""

import requests
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

YEAR = 2026
SERIES_ID = 1  # Cup Series


def get_latest_completed_race(year: int = YEAR) -> dict | None:
    url = f"https://cf.nascar.com/cacher/{year}/race_list_basic.json"
    data = requests.get(url, timeout=15).json()
    races = data.get("series_1", [])
    now = datetime.now(timezone.utc).isoformat()

    completed = [
        r for r in races
        if r.get("race_date", "") < now and r.get("actual_laps", 0) > 0
    ]
    if not completed:
        return None
    completed.sort(key=lambda x: x["race_date"], reverse=True)
    return completed[0]


def get_race_data(year: int, series_id: int, race_id: int):
    """Returns race data + the driver_id who set the single fastest lap."""
    # Main results + stage points
    feed_url = f"https://cf.nascar.com/cacher/{year}/{series_id}/{race_id}/weekend-feed.json"
    feed = requests.get(feed_url, timeout=15).json()
    race = feed["weekend_race"][0]

    # Find the single fastest lap of the race
    lap_url = f"https://cf.nascar.com/cacher/{year}/{series_id}/{race_id}/lap-times.json"
    lap_data = requests.get(lap_url, timeout=20).json()

    best_time = float("inf")
    fastest_driver_id = None

    for driver in lap_data.get("laps", []):
        did = driver["NASCARDriverID"]
        for lap in driver.get("Laps", []):
            t = lap.get("LapTime")
            if t is not None and t > 0 and t < best_time:
                best_time = t
                fastest_driver_id = did

    return race, fastest_driver_id, best_time


def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    return first, last


def main():
    print("Fetching latest completed Cup Series race...\n")

    race_meta = get_latest_completed_race()
    if not race_meta:
        print("No completed races found.")
        return

    race_id = race_meta["race_id"]
    race_name = race_meta["race_name"]
    track = race_meta["track_name"]
    race_date = race_meta["race_date"][:10]

    print(f"Race:  {race_name}")
    print(f"Track: {track}")
    print(f"Date:  {race_date}")
    print(f"ID:    {race_id}\n")

    race, fastest_driver_id, best_time = get_race_data(YEAR, SERIES_ID, race_id)
    results = race["results"]
    stage_results = race.get("stage_results", [])

    print(f"Fastest lap of the race: {best_time:.3f}s "
          f"(driver_id {fastest_driver_id})\n")

    # Stage points lookup
    stage_pts = defaultdict(lambda: {1: 0, 2: 0, 3: 0})
    for stage in stage_results:
        snum = stage["stage_number"]
        for r in stage["results"]:
            stage_pts[r["driver_id"]][snum] = r.get("stage_points", 0)

    # Build rows
    rows = []
    for r in sorted(results, key=lambda x: x["finishing_position"]):
        first, last = split_name(r.get("driver_fullname", ""))
        did = r["driver_id"]

        rows.append({
            "Position": r["finishing_position"],
            "First_Name": first,
            "Last_Name": last,
            "Points": r.get("points_earned", 0),
            "Stage_1": stage_pts[did][1],
            "Stage_2": stage_pts[did][2],
            "Stage_3": stage_pts[did][3],
            "Fastest_Lap": 1 if did == fastest_driver_id else 0,
        })

    # Preview
    print(f"{'Pos':>3}  {'First':<12} {'Last':<18} {'Pts':>4}  S1  S2  S3  Fast")
    print("-" * 65)
    for row in rows:
        print(f"{row['Position']:3}  {row['First_Name']:<12} {row['Last_Name']:<18} "
              f"{row['Points']:4}  {row['Stage_1']:2}  {row['Stage_2']:2}  "
              f"{row['Stage_3']:2}  {row['Fastest_Lap']:4}")

    # Save CSV
    output_dir = Path("nascar_results")
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / f"{race_date}_{race_id}_custom.csv"

    fieldnames = ["Position", "First_Name", "Last_Name", "Points",
                  "Stage_1", "Stage_2", "Stage_3", "Fastest_Lap"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Also save as latest.csv for easy access
    latest_path = output_dir / "latest.csv"
    with open(latest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "-" * 65)
    print(f"Saved → {csv_path}")
    print("Done.")


if __name__ == "__main__":
    main()
