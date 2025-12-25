import os
import requests
import urllib.parse

API_KEY = "123"
BASE_URL = "https://www.thesportsdb.com/api/v1/json"

LEAGUES = [
    "English Premier League",
    "NBA",
    "NFL",
    "Spanish La Liga",
    "German Bundesliga",
    "Italian Serie A",
    "French Ligue 1"
]

OUTPUT_DIR = "assets/logos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("\n--- Starting TSDB Logo Harvester ---")

def safe_name(name):
    return name.lower().replace(" ", "_").replace("/", "_")

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
        print(f"   [-] {league}: NULL teams (API restriction)")
        continue

    saved = 0

    for team in teams:
        team_name = team.get("strTeam")
        badge_url = team.get("strBadge")

        if not team_name or not badge_url:
            continue

        ext = badge_url.split(".")[-1].split("?")[0]
        if ext not in ["png", "jpg", "jpeg", "webp"]:
            continue

        filename = f"{safe_name(team_name)}.{ext}"
        filepath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(filepath):
            continue

        try:
            img = requests.get(badge_url, timeout=15)
            if img.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(img.content)
                saved += 1
        except Exception:
            continue

    print(f"   [+] {league}: Saved {saved} logos")

print("\n--- Done ---\n")
