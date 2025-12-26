import os
import json
import requests
import urllib.parse
import re
from io import BytesIO
from PIL import Image

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

# Load existing map (strict dedupe)
if os.path.exists(MAP_FILE):
    with open(MAP_FILE, "r") as f:
        image_map = json.load(f)
else:
    image_map = {}

print("\n--- Starting TSDB Logo Harvester (60x60 WEBP) ---")

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

        # STRICT 100% MATCH CHECK
        if team_name in image_map:
            continue

        slug = slugify(team_name)
        output_path = os.path.join(LOGO_DIR, f"{slug}.webp")

        if os.path.exists(output_path):
            image_map[team_name] = f"assets/logos/tsdb/{slug}"
            continue

        try:
            img_res = requests.get(badge_url, timeout=15)
            if img_res.status_code != 200:
                continue

            img = Image.open(BytesIO(img_res.content)).convert("RGBA")

            # Resize to EXACT 60x60
            img = img.resize((60, 60), Image.LANCZOS)

            # Save as WEBP
            img.save(output_path, "WEBP", quality=90, method=6)

            image_map[team_name] = f"assets/logos/tsdb/{slug}"
            saved += 1

        except Exception:
            continue

    print(f"   [+] {league}: Saved {saved} logos")

# Save updated map
with open(MAP_FILE, "w") as f:
    json.dump(image_map, f, indent=2)

print("\n--- Done ---\n")
