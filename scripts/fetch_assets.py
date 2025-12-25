import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIG
# ==========================================
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
BASE_DIR = "assets/logos"

DIRS = {
    "teams": os.path.join(BASE_DIR, "teams"),
    "leagues": os.path.join(BASE_DIR, "leagues"),
    "sports": os.path.join(BASE_DIR, "sports"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.thesportsdb.com/",
}

TARGET_LEAGUES = {
    "Premier League": "English Premier League",
    "NBA": "NBA",
    "NFL": "NFL",
    "La Liga": "Spanish La Liga",
    "F1": "Formula 1",
    "UFC": "UFC",
    "MLB": "MLB",
    "NHL": "NHL",
    "Bundesliga": "German Bundesliga",
    "Serie A": "Italian Serie A",
    "Ligue 1": "French Ligue 1",
    "Champions League": "UEFA Champions League",
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    if not name:
        return "unknown"
    name = name.lower().replace("&", "and")
    return "".join(c for c in name if c.isalnum())

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download_image(url, save_path):
    if os.path.exists(save_path):
        return False

    # Skip SVG (PIL cannot open)
    if url.lower().endswith(".svg"):
        print(f"       [!] Skipped SVG: {url}")
        return False

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            print(f"       [x] HTTP {resp.status_code}: {url}")
            return False

        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type:
            print(f"       [x] Not an image ({content_type}): {url}")
            return False

        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        img.thumbnail((60, 60), Image.Resampling.LANCZOS)

        img.save(save_path, "WEBP", quality=90)
        return True

    except Exception as e:
        print(f"       [!] Exception: {e}")
        return False

# ==========================================
# 3. FETCH LOGIC
# ==========================================
def fetch_league(tsdb_name):
    encoded = urllib.parse.quote(tsdb_name)
    url = f"{TSDB_BASE}/search_all_teams.php?l={encoded}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   [!] API Error {resp.status_code}")
            return

        data = resp.json()
        teams = data.get("teams") or []

        saved = 0
        for team in teams:
            name = team.get("strTeam")
            badge = team.get("strTeamBadge")

            if not badge:
                continue

            slug = normalize_filename(name)
            path = os.path.join(DIRS["teams"], f"{slug}.webp")

            if download_image(badge, path):
                saved += 1

        if saved:
            print(f"   [+] {tsdb_name}: Saved {saved} new logos.")
        else:
            print(f"   [=] {tsdb_name}: No new logos saved.")

    except Exception as e:
        print(f"   [!] Fatal error: {e}")

# ==========================================
# 4. MAIN
# ==========================================
def main():
    for d in DIRS.values():
        ensure_dir(d)

    print("--- Starting TSDB Logo Harvester ---")

    for i, (_, league) in enumerate(TARGET_LEAGUES.items(), 1):
        print(f" > [{i}/{len(TARGET_LEAGUES)}] {league}")
        fetch_league(league)
        time.sleep(2)

if __name__ == "__main__":
    main()
