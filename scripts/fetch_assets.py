import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO

# ==========================================
# CONFIG (CRITICAL FIX HERE)
# ==========================================
API_KEY = "1"  # ✅ REQUIRED FOR GITHUB ACTIONS
TSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

BASE_DIR = "assets/logos"
DIRS = {
    "teams": os.path.join(BASE_DIR, "teams"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "image/webp,image/*,*/*;q=0.8",
    "Referer": "https://www.thesportsdb.com/",
}

TARGET_LEAGUES = [
    "English Premier League",
    "NBA",
    "NFL",
    "Spanish La Liga",
    "Formula 1",
    "UFC",
    "MLB",
    "NHL",
    "German Bundesliga",
    "Italian Serie A",
    "French Ligue 1",
    "UEFA Champions League",
]

# ==========================================
def normalize(name):
    return "".join(c for c in name.lower() if c.isalnum())

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download_image(url, path):
    if os.path.exists(path):
        return False

    if url.lower().endswith(".svg"):
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

# ==========================================
def fetch_league(league):
    url = f"{TSDB_BASE}/search_all_teams.php?l={urllib.parse.quote(league)}"
    r = requests.get(url, timeout=15)

    data = r.json()
    teams = data.get("teams")

    if not teams:
        print(f"   [-] {league}: API returned NULL teams")
        return

    saved = 0
    for t in teams:
        name = t.get("strTeam")
        badge = t.get("strTeamBadge")
        if not badge:
            continue

        path = os.path.join(DIRS["teams"], f"{normalize(name)}.webp")
        if download_image(badge, path):
            saved += 1

    if saved:
        print(f"   [+] {league}: Saved {saved} logos")
    else:
        print(f"   [=] {league}: No new logos saved")

# ==========================================
def main():
    ensure_dir(DIRS["teams"])
    print("--- Starting TSDB Logo Harvester ---")

    for i, league in enumerate(TARGET_LEAGUES, 1):
        print(f" > [{i}/{len(TARGET_LEAGUES)}] {league}")
        fetch_league(league)
        time.sleep(2)

if __name__ == "__main__":
    main()
