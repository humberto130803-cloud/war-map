"""
War Map AI-Powered Updater
Uses Google Gemini API with Google Search grounding to classify every country's conflict status.
Runs daily via GitHub Actions.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests

DIR = Path(__file__).parent
DATA_FILE = DIR / "conflict_data.json"
LOG_FILE = DIR / "updater.log"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBeua5xjtDpoNDkfAcWle2UEnsTwZXdmMc")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# All countries we track (ISO Alpha-3 -> Name)
ALL_COUNTRIES = {
    "AFG": "Afghanistan", "ALB": "Albania", "DZA": "Algeria", "AGO": "Angola",
    "ARG": "Argentina", "ARM": "Armenia", "AUS": "Australia", "AUT": "Austria",
    "AZE": "Azerbaijan", "BHR": "Bahrain", "BGD": "Bangladesh", "BLR": "Belarus",
    "BEL": "Belgium", "BEN": "Benin", "BTN": "Bhutan", "BOL": "Bolivia",
    "BIH": "Bosnia and Herzegovina", "BWA": "Botswana", "BRA": "Brazil",
    "BRN": "Brunei", "BGR": "Bulgaria", "BFA": "Burkina Faso", "BDI": "Burundi",
    "KHM": "Cambodia", "CMR": "Cameroon", "CAN": "Canada", "CAF": "Central African Republic",
    "TCD": "Chad", "CHL": "Chile", "CHN": "China", "COL": "Colombia",
    "COG": "Republic of Congo", "COD": "Democratic Republic of Congo",
    "CRI": "Costa Rica", "CIV": "Ivory Coast", "HRV": "Croatia", "CUB": "Cuba",
    "CYP": "Cyprus", "CZE": "Czech Republic", "DNK": "Denmark", "DJI": "Djibouti",
    "DOM": "Dominican Republic", "ECU": "Ecuador", "EGY": "Egypt",
    "SLV": "El Salvador", "GNQ": "Equatorial Guinea", "ERI": "Eritrea",
    "EST": "Estonia", "SWZ": "Eswatini", "ETH": "Ethiopia", "FJI": "Fiji",
    "FIN": "Finland", "FRA": "France", "GAB": "Gabon", "GMB": "Gambia",
    "GEO": "Georgia", "DEU": "Germany", "GHA": "Ghana", "GRC": "Greece",
    "GTM": "Guatemala", "GIN": "Guinea", "GNB": "Guinea-Bissau", "GUY": "Guyana",
    "HTI": "Haiti", "HND": "Honduras", "HUN": "Hungary", "ISL": "Iceland",
    "IND": "India", "IDN": "Indonesia", "IRN": "Iran", "IRQ": "Iraq",
    "IRL": "Ireland", "ISR": "Israel", "ITA": "Italy", "JAM": "Jamaica",
    "JPN": "Japan", "JOR": "Jordan", "KAZ": "Kazakhstan", "KEN": "Kenya",
    "PRK": "North Korea", "KOR": "South Korea", "KWT": "Kuwait", "KGZ": "Kyrgyzstan",
    "LAO": "Laos", "LVA": "Latvia", "LBN": "Lebanon", "LSO": "Lesotho",
    "LBR": "Liberia", "LBY": "Libya", "LTU": "Lithuania", "LUX": "Luxembourg",
    "MDG": "Madagascar", "MWI": "Malawi", "MYS": "Malaysia", "MLI": "Mali",
    "MLT": "Malta", "MRT": "Mauritania", "MEX": "Mexico", "MDA": "Moldova",
    "MNG": "Mongolia", "MNE": "Montenegro", "MAR": "Morocco", "MOZ": "Mozambique",
    "MMR": "Myanmar", "NAM": "Namibia", "NPL": "Nepal", "NLD": "Netherlands",
    "NZL": "New Zealand", "NIC": "Nicaragua", "NER": "Niger", "NGA": "Nigeria",
    "MKD": "North Macedonia", "NOR": "Norway", "OMN": "Oman", "PAK": "Pakistan",
    "PAN": "Panama", "PNG": "Papua New Guinea", "PRY": "Paraguay", "PER": "Peru",
    "PHL": "Philippines", "POL": "Poland", "PRT": "Portugal", "QAT": "Qatar",
    "ROU": "Romania", "RUS": "Russia", "RWA": "Rwanda", "SAU": "Saudi Arabia",
    "SEN": "Senegal", "SRB": "Serbia", "SLE": "Sierra Leone", "SGP": "Singapore",
    "SVK": "Slovakia", "SVN": "Slovenia", "SOM": "Somalia", "ZAF": "South Africa",
    "SSD": "South Sudan", "ESP": "Spain", "LKA": "Sri Lanka", "SDN": "Sudan",
    "SUR": "Suriname", "SWE": "Sweden", "CHE": "Switzerland", "SYR": "Syria",
    "TWN": "Taiwan", "TJK": "Tajikistan", "TZA": "Tanzania", "THA": "Thailand",
    "TLS": "Timor-Leste", "TGO": "Togo", "TTO": "Trinidad and Tobago",
    "TUN": "Tunisia", "TUR": "Turkey", "TKM": "Turkmenistan", "UGA": "Uganda",
    "UKR": "Ukraine", "ARE": "United Arab Emirates", "GBR": "United Kingdom",
    "USA": "United States", "URY": "Uruguay", "UZB": "Uzbekistan",
    "VEN": "Venezuela", "VNM": "Vietnam", "YEM": "Yemen", "ZMB": "Zambia",
    "ZWE": "Zimbabwe", "PSE": "Palestine"
}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def ask_gemini(prompt):
    """Send a prompt to Gemini API with Google Search grounding."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.8,
            "maxOutputTokens": 8192
        }
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Extract text from response
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = ""
            for part in parts:
                if "text" in part:
                    text += part["text"]
            return text
    except Exception as e:
        log(f"Gemini API error: {e}")
        if hasattr(resp, 'text'):
            log(f"Response: {resp.text[:500]}")
    return None


def classify_countries_batch(country_list):
    """Ask Gemini to classify a batch of countries."""
    countries_str = ", ".join(country_list)

    prompt = f"""You are a geopolitical analyst. For each country listed below, classify its current military/conflict status into EXACTLY ONE of these categories:

1. "declared_war" — The country has formally declared war on another nation, or another nation has formally declared war on it
2. "active_conflict" — The country is actively engaged in armed conflict (war, civil war, insurgency, military operations) but without a formal war declaration
3. "proxy_involvement" — The country is significantly involved in a conflict through military aid, weapons supply, troop deployment, or funding to belligerents in another country's war
4. "tensions" — The country has active military standoffs, border disputes, or significant military buildups that could escalate to conflict
5. "peaceful" — The country is not involved in any significant armed conflicts or military tensions

For each country, also provide:
- A brief description of why it has that status (1-2 sentences)
- The specific conflict name if applicable
- The country's role in the conflict

IMPORTANT: Use current information from today's date. Base your classifications on actual ongoing conflicts, not historical ones.

Countries to classify: {countries_str}

Respond in this EXACT JSON format (no markdown, no code blocks, just raw JSON):
{{
  "countries": [
    {{
      "name": "CountryName",
      "status": "one_of_the_five_categories",
      "conflicts": [
        {{
          "name": "Conflict Name",
          "role": "Country's role",
          "description": "Brief description of involvement"
        }}
      ]
    }}
  ]
}}

If a country is peaceful, set conflicts to an empty array [].
"""
    return ask_gemini(prompt)


def parse_gemini_response(text):
    """Parse the JSON from Gemini's response."""
    if not text:
        return None

    # Try to extract JSON from the response
    text = text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def run_update():
    log("=" * 60)
    log("Starting War Map AI-powered update")

    # Load existing data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

    # Split countries into batches of ~40 (to stay within token limits)
    country_names = list(ALL_COUNTRIES.values())
    iso_by_name = {v.lower(): k for k, v in ALL_COUNTRIES.items()}
    batch_size = 40
    batches = [country_names[i:i+batch_size] for i in range(0, len(country_names), batch_size)]

    all_results = {}
    for i, batch in enumerate(batches):
        log(f"Processing batch {i+1}/{len(batches)} ({len(batch)} countries)...")
        response_text = classify_countries_batch(batch)

        if not response_text:
            log(f"Batch {i+1} failed — keeping existing data for these countries")
            continue

        parsed = parse_gemini_response(response_text)
        if not parsed or "countries" not in parsed:
            log(f"Batch {i+1} parse failed — response: {response_text[:300]}")
            continue

        for country in parsed["countries"]:
            name = country.get("name", "")
            iso = iso_by_name.get(name.lower())
            if not iso:
                # Try partial matching
                for full_name, code in ALL_COUNTRIES.items():
                    pass
                for cname, ccode in iso_by_name.items():
                    if name.lower() in cname or cname in name.lower():
                        iso = ccode
                        break
            if iso:
                all_results[iso] = country
                log(f"  {name}: {country.get('status', '?')}")

        # Rate limiting — be nice to the API
        if i < len(batches) - 1:
            time.sleep(5)

    # Merge results into existing data
    updated_count = 0
    for iso, result in all_results.items():
        status = result.get("status", "peaceful")
        if status not in ["declared_war", "active_conflict", "proxy_involvement", "tensions", "peaceful"]:
            status = "peaceful"

        conflicts = []
        for c in result.get("conflicts", []):
            conflict_entry = {
                "name": c.get("name", "Unknown"),
                "role": c.get("role", ""),
                "description": c.get("description", ""),
                "sources": [
                    {"title": "AI-classified via Google Search grounding", "url": "https://www.google.com/search?q=" + c.get("name", "").replace(" ", "+")}
                ]
            }
            conflicts.append(conflict_entry)

        country_name = ALL_COUNTRIES.get(iso, result.get("name", "Unknown"))
        existing_data["countries"][iso] = {
            "name": country_name,
            "status": status,
            "conflicts": conflicts
        }
        updated_count += 1

    existing_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # Save updated data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    log(f"Updated {updated_count} countries")
    log("Update complete")
    log("=" * 60)


if __name__ == "__main__":
    run_update()
