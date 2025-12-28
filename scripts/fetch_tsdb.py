import os
import requests
import urllib.parse
import re
import time
import json
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_KEY = "123" # Replace with valid key if available
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
SAVE_DIR = "assets/logos/tsdb"
LEAGUE_MAP_FILE = "assets/data/league_map.json"
REFRESH_DAYS = 60  # Redownload image if older than 60 days (Handles rebrands)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

LEAGUES = {
    "English Premier League": "English Premier League",
    "English League Championship": "English League Championship",
    "Scottish Premiership": "Scottish Premiership",
    "Spanish La Liga": "Spanish La Liga",
    "German Bundesliga": "German Bundesliga",
    "Italian Serie A": "Italian Serie A",
    "French Ligue 1": "French Ligue 1",
    "Dutch Eredivisie": "Dutch Eredivisie",
    "Portuguese Primeira Liga": "Portuguese Primeira Liga",
    "UEFA Champions League": "UEFA Champions League",
    "UEFA Europa League": "UEFA Europa League",
    "American Major League Soccer": "American Major League Soccer",
    "Saudi Pro League": "Saudi Arabian Pro League",
    "Belgian Pro League": "Belgian Pro League",
    "NBA": "NBA",
    "NFL": "NFL",
    "NHL": "NHL",
    "MLB": "MLB",
    "F1": "Formula 1",
    "UFC": "UFC",
    "Australian Big Bash League": "Australian Big Bash League",
    "United Rugby Championship": "United Rugby Championship"
}

# ==========================================
# 2. UTILS
# ==========================================
def slugify(name):
    if not name: return None
    clean = str(name).lower()
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"\s+", "-", clean)
    return clean.strip("-")

def should_download(path):
    """Returns True if file missing OR file is too old."""
    if not os.path.exists(path): return True
    
    # Check Age
    file_age_days = (time.time() - os.path.getmtime(path)) / (24 * 3600)
    if file_age_days > REFRESH_DAYS:
        return True
    return False

def save_image_optimized(url, save_path):
    """Safe save: Only overwrites if download succeeds."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode != 'RGBA': img = img.convert('RGBA')
            img = img.resize((60, 60), Image.Resampling.LANCZOS)
            
            # Save to temporary buffer first to ensure integrity
            temp_buffer = BytesIO()
            img.save(temp_buffer, "WEBP", quality=90, method=6)
            
            # Write to disk
            with open(save_path, "wb") as f:
                f.write(temp_buffer.getvalue())
            return True
    except: 
        pass
    return False

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LEAGUE_MAP_FILE), exist_ok=True)
    
    # Load Map
    league_map = {}
    if os.path.exists(LEAGUE_MAP_FILE):
        try:
            with open(LEAGUE_MAP_FILE, 'r') as f:
                league_map = json.load(f)
        except: pass

    print("--- Starting TSDB Harvester (Smart Refresh) ---")

    for display_name, tsdb_name in LEAGUES.items():
        print(f" > Checking: {display_name}")
        encoded = urllib.parse.quote(tsdb_name)
        url = f"{BASE_URL}/search_all_teams.php?l={encoded}"
        
        try:
            data = requests.get(url, headers=HEADERS, timeout=10).json()
            if data and data.get('teams'):
                count = 0
                for t in data['teams']:
                    name = t.get('strTeam')
                    if name:
                        slug = slugify(name)
                        if slug:
                            # 1. Always update map (Fixes League Shift Issue)
                            league_map[slug] = display_name

                            # 2. Check Image
                            badge = t.get('strTeamBadge') or t.get('strBadge')
                            if badge:
                                path = os.path.join(SAVE_DIR, f"{slug}.webp")
                                if should_download(path):
                                    if save_image_optimized(badge, path):
                                        count += 1
                
                if count > 0: print(f"   [+] Processed {count} updates/downloads.")
        except Exception as e:
            print(f"   [!] Error: {e}")
        
        time.sleep(1.2)

    with open(LEAGUE_MAP_FILE, 'w') as f:
        json.dump(league_map, f, indent=2)
    
    print(f"--- League Map Saved ({len(league_map)} teams) ---")

if __name__ == "__main__":
    main()
