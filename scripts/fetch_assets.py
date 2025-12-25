import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# Mimic a real browser to avoid 403 Forbidden errors on images
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://www.thesportsdb.com/'
}

TARGET_LEAGUES = {
    "Premier League": "English Premier League",
    "NBA": "NBA",
    "NFL": "NFL",
    "La Liga": "Spanish La Liga",
    "F1": "Formula 1"
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    if not name: return "unknown"
    clean = str(name).strip().replace("_", " ").replace(".", "")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def process_and_save_image(url, save_path):
    # Skip if exists
    if os.path.exists(save_path): 
        return False 
    
    try:
        # Download with timeout
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        # DEBUG: Print if image download fails
        if resp.status_code != 200:
            print(f"       [!] Image Download Failed: {resp.status_code} for {url}")
            return False

        img = Image.open(BytesIO(resp.content))
        
        if img.mode != 'RGBA': 
            img = img.convert('RGBA')
        
        img = img.resize((60, 60), Image.Resampling.LANCZOS)
        img.save(save_path, 'WEBP', quality=90)
        return True

    except Exception as e:
        print(f"       [!] Image Error: {e}")
        return False

# ==========================================
# 3. HARVESTERS
# ==========================================
def fetch_sports_logos():
    print(" > Checking Sport Icons...")
    try:
        data = requests.get(f"{TSDB_BASE}/all_sports.php", headers=HEADERS).json()
        if data.get('sports'):
            count = 0
            for s in data['sports']:
                name = s['strSport']
                url = s.get('strSportIconGreen') or s.get('strSportThumb')
                if url:
                    path = os.path.join(DIRS['sports'], f"{normalize_filename(name)}.webp")
                    if process_and_save_image(url, path): count += 1
            print(f"   [+] Saved {count} sport icons.")
    except Exception as e: 
        print(f"   [!] Sport Error: {e}")

def fetch_league_and_teams(tsdb_name):
    encoded = urllib.parse.quote(tsdb_name)
    url = f"{TSDB_BASE}/search_all_teams.php?l={encoded}"
    
    try:
        # Request API
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        # DEBUG: Check if API blocked us
        if resp.status_code != 200:
            print(f"   [!] API BLOCKED: Status {resp.status_code}")
            return

        data = resp.json()
        
        if data and data.get('teams'):
            teams = data['teams']
            print(f"   [i] Found {len(teams)} teams in {tsdb_name}. Downloading...")
            
            new_count = 0
            for t in teams:
                team_name = t.get('strTeam')
                badge_url = t.get('strTeamBadge')
                
                # DEBUG: Warn if badge is missing
                if not badge_url:
                    print(f"       [?] No badge URL for {team_name}")
                    continue

                slug = normalize_filename(team_name)
                path = os.path.join(DIRS['teams'], f"{slug}.webp")
                
                if process_and_save_image(badge_url, path):
                    new_count += 1
                    # print(f"       [+] Saved {slug}") # Uncomment to see every file
            
            print(f"   [+] Finished: {new_count} new logos saved for {tsdb_name}.")
        else:
            print(f"   [-] API returned 0 teams for {tsdb_name} (Data is null).")

    except Exception as e:
        print(f"   [!] Critical Error {tsdb_name}: {e}")

# ==========================================
# 4. MAIN
# ==========================================
def main():
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)

    print("--- 1. Harvesting Sports ---")
    fetch_sports_logos()

    print("\n--- 2. Harvesting Leagues (Debug Mode) ---")
    
    # We loop through leagues
    for common, tsdb in TARGET_LEAGUES.items():
        print(f" > Checking: {tsdb}")
        fetch_league_and_teams(tsdb)
        time.sleep(1.5)

if __name__ == "__main__":
    main()
