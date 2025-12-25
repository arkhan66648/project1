import os
import requests
import time
import re
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us" 
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# TheSportsDB API (Free Tier)
TSDB_SEARCH_TEAM = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
TSDB_SEARCH_LEAGUE = "https://www.thesportsdb.com/api/v1/json/3/searchleagues.php?l="

# ==========================================
# 2. CLEANING ENGINE (Fixes the "NBA: Team" issue)
# ==========================================
def clean_name(name):
    if not name: return ""
    name = str(name).strip()
    
    # 1. Remove prefixes like "NBA: ", "NHL: ", "Serie B: "
    # This regex removes anything before a colon if it's 2-10 chars long
    name = re.sub(r'^[A-Za-z0-9\s-]{2,15}:\s*', '', name)
    
    # 2. Remove common garbage suffixes
    name = name.replace(" W", "").replace(" U20", "")
    
    return name.strip()

def normalize_filename(name):
    # Turns "Man Utd" -> "man-utd"
    return re.sub(r'[^a-z0-9]', '-', name.lower().strip())

def is_valid_league_name(name):
    # Filter out match titles erroneously labeled as leagues
    if not name: return False
    lower = name.lower()
    if " vs " in lower or " @ " in lower or " - " in lower: return False
    if len(name) < 3: return False
    if lower in ['other', 'undefined', 'general']: return False
    return True

# ==========================================
# 3. IMAGE PROCESSING
# ==========================================
def save_image_optimized(url, save_path):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode != 'RGBA': img = img.convert('RGBA')
            
            # Resize to 60x60 (Retina ready for 20px display)
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception as e:
        pass # Silent fail to keep logs clean
    return False

# ==========================================
# 4. API FETCHING
# ==========================================
def fetch_logo_from_api(endpoint, raw_name, type_label):
    clean = clean_name(raw_name)
    if not clean: return None
    
    print(f"   > Searching {type_label}: '{clean}' (Raw: {raw_name})")
    
    try:
        # TheSportsDB Search
        res = requests.get(f"{endpoint}{clean}", timeout=5).json()
        
        # TEAMS
        if 'searchteams' in endpoint and res.get('teams'):
            return res['teams'][0].get('strTeamBadge')
            
        # LEAGUES
        elif 'searchleagues' in endpoint and res.get('leagues'):
            return res['leagues'][0].get('strBadge')
            
    except Exception:
        pass
        
    return None

# ==========================================
# 5. MAIN LOGIC
# ==========================================
def main():
    # Setup Dirs
    for path in DIRS.values():
        if not os.path.exists(path): os.makedirs(path)

    print("--- 1. Fetching Live Backend Data ---")
    try:
        data = requests.get(API_URL, timeout=15).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return

    unique_teams = set()
    unique_leagues = set()

    for m in matches:
        # Collect Teams
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        
        # Collect Leagues (Prioritize 'tournament' as it's usually cleaner)
        l_name = m.get('tournament') or m.get('league')
        if is_valid_league_name(l_name):
            unique_leagues.add(l_name)

    print(f"--- 2. Processing {len(unique_teams)} Teams ---")
    new_count = 0
    
    for team in unique_teams:
        slug = normalize_filename(clean_name(team))
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        if not os.path.exists(path):
            url = fetch_logo_from_api(TSDB_SEARCH_TEAM, team, "Team")
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_count += 1
            else:
                print(f"     [x] Not Found: {slug}")
            time.sleep(0.3) # Rate limit

    print(f"--- 3. Processing {len(unique_leagues)} Leagues ---")
    for league in unique_leagues:
        slug = normalize_filename(clean_name(league))
        path = os.path.join(DIRS['leagues'], f"{slug}.webp")
        
        if not os.path.exists(path):
            url = fetch_logo_from_api(TSDB_SEARCH_LEAGUE, league, "League")
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_count += 1
            time.sleep(0.3)

    print(f"--- DONE. Total New Logos: {new_count} ---")

if __name__ == "__main__":
    main()
