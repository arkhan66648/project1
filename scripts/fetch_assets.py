import os
import requests
import time
from PIL import Image
from io import BytesIO

# ===============================
# CONFIG (DOC-COMPLIANT)
# ===============================
API_KEY = "123"
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
SAVE_DIR = "assets/logos/teams"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.thesportsdb.com/"
}

LEAGUES = {
    "English_Premier_League": "Premier League",
    "NBA": "NBA",
    "NFL": "NFL",
    "Spanish_La_Liga": "La Liga",
    "German_Bundesliga": "Bundesliga",
    "Italian_Serie_A": "Serie A",
    "French_Ligue_1": "Ligue 1",
    "UEFA_Champions_League": "Champions League",
}

# ===============================
def normalize(name):
    return "".join(c for c in name.lower() if c.isalnum())

def download_image(url, path):
    if not url or url.endswith(".svg"):
        return False

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        if "image" not in r.headers.get("Content-Type", ""):
            return False

        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img.thumbnail((60, 60))
        img.save(path, "WEBP", quality=90)
        return True
    except:
        return False

# ===============================
def fetch_league(league_key):
    url = f"{BASE_URL}/search_all_teams.php?l={league_key}"
    r = requests.get(url, timeout=15)
    data = r.json()

    teams = data.get("teams")
    if not teams:
        print(f"   [-] {league_key}: NULL teams (API restriction)")
        return

    saved = 0
    for t in teams:
        name = t.get("strTeam")
        badge = t.get("strTeamBadge")
        if not name or not badge:
            continue

        path = os.path.join(SAVE_DIR, f"{normalize(name)}.webp")
        if download_image(badge, path):
            saved += 1

    print(f"   [+] {league_key}: Saved {saved} logos")

# ===============================
def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    print("--- Starting TSDB Logo Harvester ---")

    for i, league in enumerate(LEAGUES.keys(), 1):
        print(f" > [{i}/{len(LEAGUES)}] {league}")
        fetch_league(league)
        time.sleep(2)

if __name__ == "__main__":
    main()
