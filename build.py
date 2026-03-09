"""
Build script: embeds conflict_data.json into index.html
Run this after updating conflict_data.json to produce a working standalone HTML.
"""
import json
from pathlib import Path

DIR = Path(__file__).parent

def build():
    # Read conflict data
    with open(DIR / "conflict_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Read HTML template
    with open(DIR / "index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Embed data into HTML
    json_str = json.dumps(data, ensure_ascii=False)
    html = html.replace("CONFLICT_DATA_PLACEHOLDER", json_str)

    # Write output
    with open(DIR / "war-map.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built war-map.html with data from {data['last_updated']}")

if __name__ == "__main__":
    build()
