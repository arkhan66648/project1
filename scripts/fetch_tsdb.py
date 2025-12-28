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
API_KEY = "123" # Replace with valid key
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
SAVE_DIR = "assets/logos/tsdb"
LEAGUE_MAP_FILE = "assets/data/league_map.json"
REFRESH_DAYS = 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# --- WHITELIST CONFIGURATION ---
# Normalized list of allowed leagues (Lowercased for comparison)
ALLOWED_LEAGUES_INPUT = """
NFL, NBA, MLB, NHL, College Football, College-Football, College Basketball, College-Basketball, 
NCAAB, NCAAF, NCAA Men, NCAA-Men, NCAA Women, NCAA-Women, Premier League, Premier-League, 
Champions League, Champions-League, MLS, Bundesliga, Serie-A, Serie A, American Football, 
Ice Hockey, Ice-Hockey, Championship, Scottish Premiership, Scottish-Premiership, 
Europa League, Europa-League
"""
VALID_LEAGUES = {x.strip().lower() for x in ALLOWED_LEAGUES_INPUT.split(',') if x.strip()}

# Map Display Name -> TSDB Search Query
LEAGUES = {
    "Premier League": "English Premier League",
    "Championship": "English League Championship",
    "Scottish Premiership": "Scottish Premiership",
    "La Liga": "Spanish La Liga",
    "Bundesliga": "German Bundesliga",
    "Serie A": "Italian Serie A",
    "Ligue 1": "French Ligue 1",
    "Eredivisie": "Dutch Eredivisie",
    "Primeira Liga": "Portuguese Primeira Liga",
    "Champions League": "UEFA Champions League",
    "Europa League": "UEFA Europa League",
    "MLS": "American Major League Soccer",
    "Saudi Pro League": "Saudi Arabian Pro League",
    "NBA": "NBA",
    "NFL": "NFL",
    "NHL": "NHL",
    "MLB": "MLB",
    "F1": "Formula 1",
    "UFC": "UFC"
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
    if not os.path.exists(path): return True
    file_age_days = (time.time() - os.path.getmtime(path)) / (24 * 3600)
    return file_age_days > REFRESH_DAYS

def save_image_optimized(url, save_path):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode != 'RGBA': img = img.convert('RGBA')
            img = img.resize((60, 60), Image.Resampling.LANCZOS)
            
            temp_buffer = BytesIO()
            img.save(temp_buffer, "WEBP", quality=90, method=6)
            
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

    # --- VALIDATOR: Remove teams not in Whitelist ---
    cleaned_count = 0
    keys_to_delete = [
        k for k, v in league_map.items() 
        if str(v).lower().strip() not in VALID_LEAGUES
    ]
    for k in keys_to_delete:
        del league_map[k]
        cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"--- Removed {cleaned_count} teams with non-whitelisted leagues ---")

    print("--- Starting TSDB Harvester ---")

    for display_name, tsdb_name in LEAGUES.items():
        # Only process if this league is actually in our whitelist (fuzzy check)
        # We check if the display_name is loosely in our valid set to avoid saving unwanted leagues
        if display_name.lower() not in VALID_LEAGUES:
            # You might want to skip, or proceed if you trust LEAGUES dict.
            # For safety, we will proceed but map strict naming.
            pass

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
                            # Update Map: Always prioritize latest fetch
                            # We use 'display_name' from LEAGUES dict as the clean name
                            league_map[slug] = display_name

                            # Download Image
                            badge = t.get('strTeamBadge') or t.get('strBadge')
                            if badge:
                                path = os.path.join(SAVE_DIR, f"{slug}.webp")
                                if should_download(path):
                                    if save_image_optimized(badge, path):
                                        count += 1
                
                if count > 0: print(f"   [+] Processed {count} updates.")
        except Exception as e:
            print(f"   [!] Error: {e}")
        
        time.sleep(1.2)

    with open(LEAGUE_MAP_FILE, 'w') as f:
        json.dump(league_map, f, indent=2)
    
    print(f"--- League Map Saved ({len(league_map)} teams) ---")

if __name__ == "__main__":
    main()
