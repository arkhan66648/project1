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

# CRITICAL: These headers mimic a real Chrome browser.
# Without 'Referer' and 'Accept', TSDB image servers often return 403 Forbidden.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.thesportsdb.com/'
}

# The Leagues we want to fetch
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
    "Champions League": "UEFA Champions League"
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    if not name: return "unknown"
    # Convert "Man City" -> "man-city"
    clean = str(name).strip().replace("_", " ").replace(".", "")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def ensure_dir(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            try:
                os.remove(path)
                print(f"   [!] Deleted file blocking directory: {path}")
            except: pass
    os.makedirs(path, exist_ok=True)

def download_image(url, save_path):
    if os.path.exists(save_path): return False
    
    try:
        # 1. Download
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        # DEBUG: Print if we get blocked
        if resp.status_code != 200:
            print(f"       [x] Failed {resp.status_code}: {url}")
            return False

        # 2. Process
        img = Image.open(BytesIO(resp.content))
        
        if img.mode != 'RGBA': 
            img = img.convert('RGBA')
        
        # Resize to 60x60
        img = img.resize((60, 60), Image.Resampling.LANCZOS)
        
        # Save as WEBP
        img.save(save_path, 'WEBP', quality=90)
        return True

    except Exception as e:
        print(f"       [!] Exception: {e}")
        return False

# ==========================================
# 3. LOGIC
# ==========================================
def fetch_league(tsdb_name):
    encoded = urllib.parse.quote(tsdb_name)
    url = f"{TSDB_BASE}/search_all_teams.php?l={encoded}"
    
    try:
        # Call API
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code != 200:
            print(f"   [!] API Error {resp.status_code} for {tsdb_name}")
            return

        data = resp.json()
        
        # Check if teams exist
        if data and data.get('teams'):
            teams = data['teams']
            # print(f"   [i] Found {len(teams)} teams in {tsdb_name}...")
            
            saved_count = 0
            for t in teams:
                name = t.get('strTeam')
                badge_url = t.get('strTeamBadge')
                
                # Case 1: No Badge URL in API
                if not badge_url:
                    # print(f"       [?] No badge data for {name}") 
                    continue
                
                # Case 2: Have URL, try download
                slug = normalize_filename(name)
                path = os.path.join(DIRS['teams'], f"{slug}.webp")
                
                if download_image(badge_url, path):
                    saved_count += 1
            
            if saved_count > 0:
                print(f"   [+] {tsdb_name}: Saved {saved_count} new logos.")
            else:
                print(f"   [=] {tsdb_name}: No new logos saved (All exist or failed).")
                
        else:
            print(f"   [-] {tsdb_name}: API returned NULL teams.")

    except Exception as e:
        print(f"   [!] Critical connection error: {e}")

# ==========================================
# 4. MAIN
# ==========================================
def main():
    for d in DIRS.values(): ensure_dir(d)

    print("--- Starting TSDB Only Harvester ---")
    
    total = len(TARGET_LEAGUES)
    for i, (common, tsdb) in enumerate(TARGET_LEAGUES.items()):
        print(f" > [{i+1}/{total}] Processing: {tsdb}")
        fetch_league(tsdb)
        
        # Sleep 2 seconds to be safe on Free Tier
        time.sleep(2.0)

if __name__ == "__main__":
    main()
