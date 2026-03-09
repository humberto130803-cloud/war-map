"""
War Map AI-Powered Updater
1. Scrapes conflict data from ACLED, CFR, ICG, and news sources
2. Feeds scraped data to Groq (Llama 3.3 70B) for country classification
3. Updates conflict_data.json
Runs daily via GitHub Actions.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    os.system(f"{sys.executable} -m pip install requests beautifulsoup4")
    import requests
    from bs4 import BeautifulSoup

DIR = Path(__file__).parent
DATA_FILE = DIR / "conflict_data.json"
LOG_FILE = DIR / "updater.log"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {"User-Agent": "WarMapBot/1.0 (conflict-tracker; educational)"}

# All countries
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


# ── Source scrapers ──────────────────────────────────────────────────

def scrape_cfr():
    """Scrape CFR Global Conflict Tracker."""
    try:
        url = "https://www.cfr.org/global-conflict-tracker"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            # Extract conflict-related paragraphs
            lines = [l for l in text.split("\n") if len(l) > 40 and any(
                kw in l.lower() for kw in ["conflict", "war", "crisis", "violence", "military", "attack", "insurgency"]
            )]
            result = "\n".join(lines[:80])
            log(f"CFR: scraped {len(lines)} relevant lines")
            return result
    except Exception as e:
        log(f"CFR scrape failed: {e}")
    return ""


def scrape_acled():
    """Scrape ACLED conflict data/dashboard."""
    try:
        url = "https://acleddata.com/conflict-watchlist/"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if len(l) > 40]
            result = "\n".join(lines[:80])
            log(f"ACLED: scraped {len(lines)} lines")
            return result
    except Exception as e:
        log(f"ACLED scrape failed: {e}")
    return ""


def scrape_icg():
    """Scrape International Crisis Group."""
    try:
        url = "https://www.crisisgroup.org/crisiswatch"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if len(l) > 40]
            result = "\n".join(lines[:80])
            log(f"ICG: scraped {len(lines)} lines")
            return result
    except Exception as e:
        log(f"ICG scrape failed: {e}")
    return ""


def scrape_reuters_conflicts():
    """Scrape Reuters world news for conflict headlines."""
    try:
        url = "https://www.reuters.com/world/"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            headlines = []
            for tag in soup.find_all(["h2", "h3", "a"]):
                text = tag.get_text(strip=True)
                if len(text) > 20 and any(kw in text.lower() for kw in [
                    "war", "conflict", "attack", "military", "strike", "bomb",
                    "troops", "invasion", "missile", "ceasefire", "sanctions",
                    "insurgent", "rebel", "fighting", "killed", "weapons"
                ]):
                    headlines.append(text)
            result = "\n".join(list(set(headlines))[:50])
            log(f"Reuters: found {len(headlines)} conflict headlines")
            return result
    except Exception as e:
        log(f"Reuters scrape failed: {e}")
    return ""


def scrape_aljazeera():
    """Scrape Al Jazeera for conflict news."""
    try:
        url = "https://www.aljazeera.com/tag/war-and-conflict/"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            headlines = []
            for tag in soup.find_all(["h2", "h3", "a"]):
                text = tag.get_text(strip=True)
                if len(text) > 25:
                    headlines.append(text)
            result = "\n".join(list(set(headlines))[:50])
            log(f"Al Jazeera: found {len(headlines)} headlines")
            return result
    except Exception as e:
        log(f"Al Jazeera scrape failed: {e}")
    return ""


# ── Groq AI Classification ──────────────────────────────────────────

def ask_groq(messages, max_tokens=4096, retries=3):
    """Send a request to Groq API with retry on rate limits."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_URL, json=payload, timeout=120,
                                 headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                                          "Content-Type": "application/json"})
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                log(f"Rate limited, waiting {wait}s (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            log(f"Groq API error: {e}")
            if hasattr(resp, "text"):
                log(f"Response: {resp.text[:300]}")
            if attempt < retries - 1:
                time.sleep(10)
    return None


def classify_batch(country_batch, scraped_context):
    """Ask Groq to classify a batch of countries using scraped context."""
    countries_str = ", ".join(country_batch)

    messages = [
        {
            "role": "system",
            "content": """You are a geopolitical analyst. You classify countries' conflict status based on provided source data from ACLED, CFR, ICG, Reuters, and Al Jazeera. Be accurate and conservative — only classify a country as in conflict if the evidence clearly supports it.

Categories:
1. "declared_war" — Formal declaration of war exists
2. "active_conflict" — Actively engaged in armed conflict (war, civil war, insurgency, direct military operations) without formal declaration
3. "proxy_involvement" — Significantly involved through military aid, weapons supply, troop deployment, or funding to belligerents in another country's war
4. "tensions" — Active military standoffs, border disputes, or significant military buildups
5. "peaceful" — Not involved in significant armed conflicts

Respond ONLY with valid JSON, no markdown, no explanation."""
        },
        {
            "role": "user",
            "content": f"""Based on the following current conflict data from multiple sources, classify each country listed below.

=== SOURCE DATA ===
{scraped_context[:12000]}
=== END SOURCE DATA ===

Countries to classify: {countries_str}

For each country respond with this exact JSON structure:
{{
  "countries": [
    {{
      "name": "CountryName",
      "status": "category_string",
      "conflicts": [
        {{
          "name": "Conflict Name",
          "role": "Country's role",
          "description": "1-2 sentence explanation"
        }}
      ]
    }}
  ]
}}

If peaceful, set conflicts to []. Classify ALL {len(country_batch)} countries listed above."""
        }
    ]

    return ask_groq(messages, max_tokens=4096)


def parse_response(text):
    """Parse JSON from Groq response."""
    if not text:
        return None
    text = text.strip()
    # Remove markdown code blocks
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


# ── Main ─────────────────────────────────────────────────────────────

def run_update():
    log("=" * 60)
    log("Starting War Map AI-powered update (Groq + multi-source)")

    # Step 1: Scrape sources
    log("Scraping conflict sources...")
    sources = []

    cfr = scrape_cfr()
    if cfr:
        sources.append(f"=== CFR GLOBAL CONFLICT TRACKER ===\n{cfr}")

    acled = scrape_acled()
    if acled:
        sources.append(f"=== ACLED CONFLICT WATCHLIST ===\n{acled}")

    icg = scrape_icg()
    if icg:
        sources.append(f"=== INTERNATIONAL CRISIS GROUP ===\n{icg}")

    reuters = scrape_reuters_conflicts()
    if reuters:
        sources.append(f"=== REUTERS CONFLICT HEADLINES ===\n{reuters}")

    aljazeera = scrape_aljazeera()
    if aljazeera:
        sources.append(f"=== AL JAZEERA WAR & CONFLICT ===\n{aljazeera}")

    if not sources:
        log("ERROR: No sources could be scraped. Aborting update.")
        return

    scraped_context = "\n\n".join(sources)
    log(f"Total scraped context: {len(scraped_context)} characters from {len(sources)} sources")

    # Step 2: Load existing data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

    # Step 3: Classify in batches
    country_names = list(ALL_COUNTRIES.values())
    iso_by_name = {}
    for k, v in ALL_COUNTRIES.items():
        iso_by_name[v.lower()] = k
        # Add common aliases
        if v == "United States":
            iso_by_name["us"] = k
            iso_by_name["usa"] = k
            iso_by_name["united states of america"] = k
        elif v == "United Kingdom":
            iso_by_name["uk"] = k
        elif v == "Democratic Republic of Congo":
            iso_by_name["drc"] = k
            iso_by_name["dr congo"] = k
        elif v == "Republic of Congo":
            iso_by_name["congo"] = k
        elif v == "Ivory Coast":
            iso_by_name["cote d'ivoire"] = k
            iso_by_name["côte d'ivoire"] = k

    batch_size = 35
    batches = [country_names[i:i+batch_size] for i in range(0, len(country_names), batch_size)]
    all_results = {}

    for i, batch in enumerate(batches):
        log(f"Classifying batch {i+1}/{len(batches)} ({len(batch)} countries)...")
        response_text = classify_batch(batch, scraped_context)

        if not response_text:
            log(f"  Batch {i+1} failed — keeping existing data")
            continue

        parsed = parse_response(response_text)
        if not parsed or "countries" not in parsed:
            log(f"  Batch {i+1} parse failed. Response preview: {response_text[:200]}")
            continue

        for country in parsed["countries"]:
            name = country.get("name", "")
            iso = iso_by_name.get(name.lower())
            if not iso:
                # Fuzzy match
                for cname, ccode in iso_by_name.items():
                    if name.lower() in cname or cname in name.lower():
                        iso = ccode
                        break
            if iso:
                all_results[iso] = country
                status = country.get("status", "?")
                if status != "peaceful":
                    log(f"  {name}: {status}")

        # Rate limit: Groq free tier has TPM limits
        if i < len(batches) - 1:
            time.sleep(15)

    log(f"Classified {len(all_results)} countries total")

    # Step 4: Merge results
    valid_statuses = {"declared_war", "active_conflict", "proxy_involvement", "tensions", "peaceful"}
    updated = 0

    for iso, result in all_results.items():
        status = result.get("status", "peaceful")
        if status not in valid_statuses:
            status = "peaceful"

        conflicts = []
        for c in result.get("conflicts", []):
            conflict_name = c.get("name", "Unknown Conflict")
            conflicts.append({
                "name": conflict_name,
                "role": c.get("role", ""),
                "description": c.get("description", ""),
                "sources": [
                    {"title": f"Search: {conflict_name}",
                     "url": "https://www.google.com/search?q=" + conflict_name.replace(" ", "+") + "+2026"}
                ]
            })

        existing_data["countries"][iso] = {
            "name": ALL_COUNTRIES.get(iso, result.get("name", "Unknown")),
            "status": status,
            "conflicts": conflicts
        }
        updated += 1

    existing_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    log(f"Updated {updated} countries in conflict_data.json")
    log("Update complete")
    log("=" * 60)


if __name__ == "__main__":
    run_update()
