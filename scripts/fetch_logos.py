import os
import requests
import time
import re
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
# We use the 'all' endpoint or 'US' to get maximum coverage
API_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us" 

BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# TheSportsDB API
TSDB_SEARCH_TEAM = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
TSDB_SEARCH_LEAGUE = "https://www.thesportsdb.com/api/v1/json/3/searchleagues.php?l="
TSDB_SEARCH_SPORT = "https://www.thesportsdb.com/api/v1/json/3/all_sports.php" # We will filter this list

# MAPPING: Your JSON 'sport' slug -> TheSportsDB 'strSport' name
SPORT_MAPPING = {
    "americanfootball": "American Football",
    "basketball": "Basketball",
    "icehockey": "Ice Hockey",
    "soccer": "Soccer",
    "baseball": "Baseball",
    "tennis": "Tennis",
    "cricket": "Cricket",
    "rugby": "Rugby",
    "mma": "Fighting",
    "boxing": "Fighting",
    "golf": "Golf",
    "motorsport": "Motorsport"
}

# ==========================================
# 2. DATA CLEANING ENGINE
# ==========================================
def clean_team_name(name):
    """
    Input: "NBA: Charlotte Hornets" -> Output: "Charlotte Hornets"
    Input: "Northwestern" -> Output: "Northwestern"
    """
    if not name: return ""
    name = str(name).strip()
    
    # Regex: Remove any prefix ending in a colon (e.g., "NBA: ", "Serie A: ")
    # This matches characters at the start until ': '
    cleaned = re.sub(r'^.*?: ', '', name)
    
    # Remove common garbage like ' U20' or ' W' if not part of the core name
    # (Optional, be careful not to remove real parts)
    
    return cleaned.strip()

def normalize_filename(name):
    """
    Input: "Charlotte Hornets" -> Output: "charlotte-hornets"
    """
    if not name: return "unknown"
    return re.sub(r'[^a-z0-9]', '-', name.lower().strip())

# ==========================================
# 3. IMAGE PROCESSING
# ==========================================
def save_image_optimized(url, save_path):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            
            # Ensure transparency support
            if img.mode != 'RGBA': 
                img = img.convert('RGBA')
            
            # RESIZE: 60x60px (Retina ready for your 20px CSS letters)
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception:
        pass # Fail silently
    return False

# ==========================================
# 4. FETCHING LOGIC
# ==========================================
def fetch_api_logo(endpoint, query_name, extract_key):
    """Generic fetcher for TSDB"""
    try:
        res = requests.get(f"{endpoint}{query_name}", timeout=5).json()
        
        # Teams
        if 'searchteams' in endpoint and res.get('teams'):
            return res['teams'][0].get(extract_key)
        
        # Leagues
        elif 'searchleagues' in endpoint and res.get('leagues'):
            return res['leagues'][0].get(extract_key)
            
    except Exception:
        pass
    return None

def fetch_sport_thumb(sport_name):
    """Fetches sport thumbnail from 'all_sports.php'"""
    try:
        res = requests.get(TSDB_SEARCH_SPORT, timeout=5).json()
        if res.get('sports'):
            for s in res['sports']:
                if s.get('strSport') == sport_name:
                    return s.get('strSportIconGreen') or s.get('strSportThumb')
    except: pass
    return None

# ==========================================
# 5. MAIN HARVESTER
# ==========================================
def main():
    # 1. Setup Directories
    for path in DIRS.values():
        if not os.path.exists(path): os.makedirs(path)

    print("--- 1. Fetching Backend Data ---")
    try:
        # Your API returns { "country": "...", "matches": [ ... ] }
        data = requests.get(API_URL).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: Failed to load backend. {e}")
        return

    unique_teams = set()
    unique_leagues = set()
    unique_sports = set()

    # 2. Extract Data from JSON
    for m in matches:
        # TEAMS
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        
        # LEAGUES (Prioritize 'tournament', fallback to 'league')
        lg = m.get('tournament') or m.get('league')
        if lg and lg.lower() not in ['undefined', 'general', 'other']:
            unique_leagues.add(lg)
            
        # SPORTS
        sp = m.get('sport')
        if sp: unique_sports.add(sp)

    print(f"--- Found: {len(unique_teams)} Teams, {len(unique_leagues)} Leagues, {len(unique_sports)} Sports ---")

    # 3. Process TEAMS
    new_teams = 0
    for raw_name in unique_teams:
        clean = clean_team_name(raw_name)     # e.g., "Charlotte Hornets"
        slug = normalize_filename(clean)      # e.g., "charlotte-hornets"
        
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching Team: '{clean}'...")
            url = fetch_api_logo(TSDB_SEARCH_TEAM, clean, 'strTeamBadge')
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_teams += 1
            else:
                # Fallback: Try searching only the last word if it's long? 
                # (Optional optimization, skipping for safety)
                print(f"     [-] Not found")
            time.sleep(0.2) # Rate limit

    # 4. Process LEAGUES
    new_leagues = 0
    for lg_name in unique_leagues:
        slug = normalize_filename(lg_name)
        path = os.path.join(DIRS['leagues'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching League: '{lg_name}'...")
            url = fetch_api_logo(TSDB_SEARCH_LEAGUE, lg_name, 'strBadge')
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_leagues += 1
            time.sleep(0.2)

    # 5. Process SPORTS
    for sp_slug in unique_sports:
        # Use Mapping: 'americanfootball' -> 'American Football'
        search_name = SPORT_MAPPING.get(sp_slug.lower(), sp_slug.capitalize())
        
        # We save it as the SLUG so the frontend can find it easily
        # e.g. assets/logos/sports/americanfootball.webp
        path = os.path.join(DIRS['sports'], f"{sp_slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching Sport: '{search_name}'...")
            url = fetch_sport_thumb(search_name)
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {sp_slug}.webp")

    print(f"--- DONE. New Teams: {new_teams}, New Leagues: {new_leagues} ---")

if __name__ == "__main__":
    main()
