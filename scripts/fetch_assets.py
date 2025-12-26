import os
import json
import requests
import urllib.parse
import re

API_KEY = "123"
BASE_URL = "https://www.thesportsdb.com/api/v1/json"

LEAGUES = [
    "NFL",
    "NBA",
    "MLB",
    "NHL",
    "MLS",
    "English Premier League",
    "Championship",
    "Scottish Premiership",
    "Spanish La Liga",
    "German Bundesliga",
    "Italian Serie A",
    "French Ligue 1"
]

LOGO_DIR = "assets/logos/tsdb"
MAP_FILE = "assets/data/image_map.json"

os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)

def slugify(name):
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return name.strip("-")

# Load existing map (for strict dedupe)
if os.path.exists(MAP_FILE):
    with open(MAP_FILE, "r") as f:
        image_map = json.load(f)
else:
    image_map = {}

print("\n--- Starting TSDB Logo Harvester ---")

for idx, league in enumerate(LEAGUES, start=1):
    print(f" > [{idx}/{len(LEAGUES)}] {league}")

    league_q = urllib.parse.quote(league)
    url = f"{BASE_URL}/{API_KEY}/search_all_teams.php?l={league_q}"

    try:
        res = requests.get(url, timeout=15)
        data = res.json()
    except Exception as e:
        print(f"   [!] Request failed: {e}")
        continue

    teams = data.get("teams")
    if not teams:
        print(f"   [-] {league}: No teams returned")
        continue

    saved = 0

    for team in teams:
        team_name = team.get("strTeam")
        badge_url = team.get("strBadge")

        if not team_name or not badge_url:
            continue

        slug = slugify(team_name)

        # STRICT 100% MATCH DEDUPE
        if team_name in image_map:
            continue

        ext = badge_url.split(".")[-1].split("?")[0].lower()
        if ext not in ["png", "jpg", "jpeg", "webp"]:
            continue

        filename = f"{slug}.{ext}"
        filepath = os.path.join(LOGO_DIR, filename)

        if os.path.exists(filepath):
            image_map[team_name] = f"assets/logos/tsdb/{slug}"
            continue

        try:
            img = requests.get(badge_url, timeout=15)
            if img.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(img.content)

                image_map[team_name] = f"assets/logos/tsdb/{slug}"
                saved += 1
        except Exception:
            continue

    print(f"   [+] {league}: Saved {saved} logos")

# Save updated map
with open(MAP_FILE, "w") as f:
    json.dump(image_map, f, indent=2)

print("\n--- Done ---\n")
