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
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

# Directory Setup
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# Known mappings to help the API find leagues
LEAGUE_FIXES = {
    "Premier League": "English Premier League",
    "Serie A": "Italian Serie A",
    "La Liga": "Spanish La Liga",
    "Bundesliga": "German Bundesliga",
    "Ligue 1": "French Ligue 1",
    "Championship": "English League Championship",
    "Eredivisie": "Dutch Eredivisie",
    "Primeira Liga": "Portuguese Primeira Liga",
    "NBA": "NBA",
    "NHL": "NHL",
    "NFL": "NFL"
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    clean = str(name).strip().replace("_", " ")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def save_image(url, save_path):
    if os.path.exists(save_path): return False # Skip if exists
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
# 3. LEAGUE-BASED FETCHING
# ==========================================
def get_league_id(league_name):
    """Search for a league and get its ID"""
    # 1. Clean name
    search_name = LEAGUE_FIXES.get(league_name, league_name)
    search_name = search_name.replace("_", " ").split(":")[0].strip() # Remove "Serie B: Venezia" prefixes
    
    endpoint = f"{TSDB_BASE}/searchleague.php?l={urllib.parse.quote(search_name)}"
    
    try:
        data = requests.get(endpoint, headers=HEADERS, timeout=5).json()
        if data and data.get('leagues'):
            return data['leagues'][0]['idLeague']
    except: pass
    return None

def fetch_teams_by_league(league_id):
    """Get ALL teams in a league (Efficiency: 1 req = 20 teams)"""
    endpoint = f"{TSDB_BASE}/lookup_all_teams.php?id={league_id}"
    teams_map = {} # { "arsenal": "url", "manchesterunited": "url" }
    
    try:
        data = requests.get(endpoint, headers=HEADERS, timeout=5).json()
        if data and data.get('teams'):
            for t in data['teams']:
                if t.get('strTeamBadge'):
                    # Create a normalized key for matching later
                    key = normalize_filename(t['strTeam'])
                    teams_map[key] = t['strTeamBadge']
    except: pass
    return teams_map

# ==========================================
# 4. MAIN
# ==========================================
def main():
    for path in DIRS.values():
        os.makedirs(path, exist_ok=True)

    print("--- 1. Getting Match Data ---")
    try:
        data = requests.get(MATCH_SOURCE_URL, headers=HEADERS).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return

    # 1. Group Teams by League
    # We want to know which leagues we need to fetch
    needed_leagues = set()
    all_target_teams = set()
    
    for m in matches:
        lg = m.get('tournament') or m.get('league')
        if lg: needed_leagues.add(lg)
        
        if m.get('team_a'): all_target_teams.add(normalize_filename(m['team_a']))
        if m.get('team_b'): all_target_teams.add(normalize_filename(m['team_b']))

    print(f"--- 2. Identified {len(needed_leagues)} Leagues & {len(all_target_teams)} Teams ---")

    # 2. Build a Local Database of Logos
    local_logo_db = {} # { "team-slug": "url_from_api" }

    for i, lg_name in enumerate(needed_leagues):
        print(f" > [{i+1}/{len(needed_leagues)}] Processing League: {lg_name}")
        
        lid = get_league_id(lg_name)
        if lid:
            # Get all teams in this league
            teams = fetch_teams_by_league(lid)
            local_logo_db.update(teams)
            print(f"   [+] Found {len(teams)} teams in {lg_name}")
        else:
            print(f"   [-] League ID not found (Restricted?)")
        
        time.sleep(1.5) # Be nice to the API

    # 3. Match & Download
    print(f"--- 3. Matching & Downloading Logos ---")
    download_count = 0
    
    for target_slug in all_target_teams:
        save_path = os.path.join(DIRS['teams'], f"{target_slug}.webp")
        
        # If we already have it locally, skip
        if os.path.exists(save_path): continue

        # Try exact match
        img_url = local_logo_db.get(target_slug)
        
        # If no exact match, try fuzzy matching (e.g. "man-utd" vs "manchester-united")
        if not img_url:
            keys = list(local_logo_db.keys())
            matches = get_close_matches(target_slug, keys, n=1, cutoff=0.7)
            if matches:
                img_url = local_logo_db[matches[0]]

        if img_url:
            if save_image(img_url, save_path):
                print(f"   [+] Saved: {target_slug}")
                download_count += 1
        else:
            pass # Silently fail for teams we couldn't find in any league

    print(f"--- DONE. Downloaded {download_count} new logos. ---")

if __name__ == "__main__":
    main()
