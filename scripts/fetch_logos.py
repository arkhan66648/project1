import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO
from difflib import get_close_matches

# ==========================================
# 1. CONFIGURATION
# ==========================================
MATCH_SOURCE_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us" 
# DOCS: "The current free API key is: 3"
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# DOCS: We must map your source names to TSDB "Official" League Names
# Use this to translate what your API gives to what TSDB expects
LEAGUE_MAP = {
    "Premier League": "English Premier League",
    "Championship": "English League Championship",
    "League One": "English League One",
    "League Two": "English League Two",
    "Serie A": "Italian Serie A",
    "Serie B": "Italian Serie B",
    "La Liga": "Spanish La Liga",
    "Bundesliga": "German Bundesliga",
    "Ligue 1": "French Ligue 1",
    "Eredivisie": "Dutch Eredivisie",
    "Primeira Liga": "Portuguese Primeira Liga",
    "NBA": "NBA",
    "NHL": "NHL",
    "NFL": "NFL",
    "MLB": "Major League Baseball",
    "Euroleague": "Euroleague Basketball",
    "Champions League": "UEFA Champions League",
    "Europa League": "UEFA Europa League",
    "SA20": "South African SA20",
    "Big Bash League": "Australian Big Bash League",
    "Men's Big Bash League": "Australian Big Bash League",
    "United Rugby Championship": "United Rugby Championship"
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    clean = str(name).strip().replace("_", " ")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def ensure_dir(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
    os.makedirs(path, exist_ok=True)

def save_image(url, save_path):
    if os.path.exists(save_path): return False
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode != 'RGBA': img = img.convert('RGBA')
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            img.save(save_path, 'WEBP', quality=90)
            return True
    except: pass
    return False

# ==========================================
# 3. CORE LOGIC (Using search_all_teams.php)
# ==========================================
def fetch_league_teams(league_name):
    """
    DOCS: "List all the teams in a specific league by the leagues name"
    URL: search_all_teams.php?l=English Premier League
    """
    # 1. Map to TSDB Name (e.g. "Premier League" -> "English Premier League")
    tsdb_name = LEAGUE_MAP.get(league_name, league_name)
    
    encoded_name = urllib.parse.quote(tsdb_name)
    endpoint = f"{TSDB_BASE}/search_all_teams.php?l={encoded_name}"
    
    teams_map = {} 
    
    try:
        data = requests.get(endpoint, headers=HEADERS, timeout=10).json()
        
        # Check if we got teams back
        if data and data.get('teams'):
            for t in data['teams']:
                if t.get('strTeamBadge'):
                    # Save local map: "arsenal" -> URL
                    key = normalize_filename(t['strTeam'])
                    teams_map[key] = t['strTeamBadge']
                    
                    # Also map alternate names if available
                    if t.get('strAlternate'):
                        key_alt = normalize_filename(t['strAlternate'])
                        teams_map[key_alt] = t['strTeamBadge']
                        
        else:
            # Debug: Print why it failed
            print(f"     [-] No teams found for '{tsdb_name}'. (Check spelling?)")

    except Exception as e:
        pass
        
    return teams_map

# ==========================================
# 4. MAIN
# ==========================================
def main():
    for path in DIRS.values(): ensure_dir(path)

    print("--- 1. Getting Match Data ---")
    try:
        data = requests.get(MATCH_SOURCE_URL, headers=HEADERS).json()
        matches = data.get('matches', [])
    except: return

    # 1. Filter Valid Leagues
    needed_leagues = set()
    all_target_teams = set()
    
    for m in matches:
        lg = m.get('tournament') or m.get('league')
        if lg:
            # FILTER: Remove garbage entries that are actually Matches or Sports
            lg_lower = lg.lower()
            if " - " in lg or " @ " in lg or " vs " in lg: continue # Skip "Chelsea - Aston Villa"
            if lg_lower in ["baseball", "basketball", "football", "fight", "other", "rugby", "cricket"]: continue
            
            needed_leagues.add(lg)
        
        if m.get('team_a'): all_target_teams.add(normalize_filename(m['team_a']))
        if m.get('team_b'): all_target_teams.add(normalize_filename(m['team_b']))

    print(f"--- 2. Identified {len(needed_leagues)} Valid Leagues & {len(all_target_teams)} Teams ---")

    # 2. Build Logo Database
    local_logo_db = {} 

    for i, lg_name in enumerate(needed_leagues):
        print(f" > [{i+1}/{len(needed_leagues)}] Fetching: {lg_name}")
        
        # Call the "List All Teams" endpoint
        teams = fetch_league_teams(lg_name)
        
        if teams:
            local_logo_db.update(teams)
            print(f"   [+] Cached {len(teams)} logos")
        
        # DOCS: "Free users 30 requests per minute" -> Sleep 2s
        time.sleep(2.0) 

    # 3. Match & Download
    print(f"--- 3. Saving Images ---")
    count = 0
    for target_slug in all_target_teams:
        save_path = os.path.join(DIRS['teams'], f"{target_slug}.webp")
        if os.path.exists(save_path): continue

        img_url = local_logo_db.get(target_slug)
        
        # Fuzzy Match Fallback
        if not img_url:
            keys = list(local_logo_db.keys())
            matches = get_close_matches(target_slug, keys, n=1, cutoff=0.8)
            if matches: img_url = local_logo_db[matches[0]]

        if img_url and save_image(img_url, save_path):
            print(f"   [+] Saved: {target_slug}")
            count += 1

    print(f"--- DONE. New logos: {count} ---")

if __name__ == "__main__":
    main()
