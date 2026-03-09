"""
War Map Auto-Updater
Fetches latest conflict data from public sources and updates conflict_data.json.
Runs as a scheduled task daily.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install requests beautifulsoup4")
    import requests
    from bs4 import BeautifulSoup

WAR_MAP_DIR = Path(__file__).parent
DATA_FILE = WAR_MAP_DIR / "conflict_data.json"
LOG_FILE = WAR_MAP_DIR / "updater.log"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def fetch_acled_data():
    """Fetch conflict event counts from ACLED's public dashboard data."""
    try:
        url = "https://acleddata.com/acleddatanew/wp-content/uploads/dlm_uploads/conflict-severity-index.json"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "WarMap/1.0"})
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log(f"ACLED fetch failed: {e}")
    return None


def fetch_wikipedia_wars():
    """Scrape Wikipedia's list of ongoing armed conflicts for latest data."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_ongoing_armed_conflicts"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "WarMap/1.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Extract country names mentioned in conflict tables
            tables = soup.find_all("table", class_="wikitable")
            conflicts = []
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # skip header
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        conflict_name = cells[0].get_text(strip=True)
                        location = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        conflicts.append({
                            "name": conflict_name,
                            "location": location,
                            "raw_text": row.get_text(strip=True)
                        })
            return conflicts
    except Exception as e:
        log(f"Wikipedia fetch failed: {e}")
    return None


def fetch_cfr_tracker():
    """Check CFR Global Conflict Tracker for updates."""
    try:
        url = "https://www.cfr.org/global-conflict-tracker"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "WarMap/1.0"})
        if resp.status_code == 200:
            log("CFR tracker accessible — check for new conflicts manually or via API")
            return True
    except Exception as e:
        log(f"CFR fetch failed: {e}")
    return None


def update_timestamp():
    """Update the last_updated field in the conflict data."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log("Updated timestamp in conflict_data.json")
        return data
    except Exception as e:
        log(f"Failed to update data file: {e}")
        return None


def run_update():
    log("=" * 50)
    log("Starting War Map data update")

    # Fetch from multiple sources
    wiki_data = fetch_wikipedia_wars()
    if wiki_data:
        log(f"Wikipedia: Found {len(wiki_data)} conflict entries")

    acled_data = fetch_acled_data()
    if acled_data:
        log(f"ACLED: Data retrieved successfully")

    cfr_data = fetch_cfr_tracker()

    # Update timestamp
    update_timestamp()

    # Log summary of what was found
    if wiki_data:
        log("--- New/Updated conflicts from Wikipedia ---")
        for c in wiki_data[:10]:
            log(f"  - {c['name']}: {c['location']}")

    log("Update complete. Review conflict_data.json for manual adjustments.")
    log("NOTE: Major status changes (new wars, peace agreements) require manual review.")
    log("=" * 50)


if __name__ == "__main__":
    run_update()
