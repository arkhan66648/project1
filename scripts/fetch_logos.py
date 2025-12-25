import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us" 

# Directory Setup
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# --- FIX: USE V1 BASE URL FOR FREE TIER ---
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Mapping specific sport slugs to TSDB names
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
# 2. NAME CLEANING & FORMATTING
# ==========================================
def clean_name(name):
    if not name: return ""
    name = str(name).strip()
    name = name.replace("_", " ") # Convert backend underscores to spaces
    
    # Remove "NBA: ", "NHL: " pattern
    name = re.sub(r'^[A-Za-z0-9\s-]{2,15}:\s*', '', name)
    
    # Remove common suffixes
    name = name.replace(" U20", "").replace(" W", "")
    
    return name.strip()

def normalize_filename(name):
    """
    Filename safe: 'Los Angeles Lakers' -> 'los-angeles-lakers'
    """
    clean = str(name).strip().replace("_", " ")
    return re.sub(r'[^a-z0-9]', '-', clean.lower().strip())

# ==========================================
# 3. IMAGE PROCESSING
# ==========================================
import re # Added import re here just in case

def save_image_optimized(url, save_path):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            
            if img.mode != 'RGBA': 
                img = img.convert('RGBA')
            
            # Resize to 60x60px
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception:
        pass
    return False

# ==========================================
# 4. API FETCHING (V1 STRUCTURE)
# ==========================================
def fetch_logo_v1(category, raw_name):
    """
    category: 'team' or 'league'
    raw_name: 'Manchester United' (Spaces, not underscores)
    """
    
    # Clean the name (remove prefixes, swap underscores for spaces)
    clean = clean_name(raw_name)
    encoded_name = urllib.parse.quote(clean) # Encodes spaces to %20
    
    endpoint = ""
    
    # --- FIX: USE V1 PHP ENDPOINTS ---
    if category == 'team':
        endpoint = f"{TSDB_BASE}/searchteams.php?t={encoded_name}"
    elif category == 'league':
        endpoint = f"{TSDB_BASE}/searchleague.php?l={encoded_name}"
        
    try:
        res = requests.get(endpoint, headers=HEADERS, timeout=5)
        if res.status_code != 200: return None
        
        data = res.json()
        
        # Handle TEAM response
        if category == 'team' and data.get('teams'):
            return data['teams'][0].get('strTeamBadge')
            
        # Handle LEAGUE response
        elif category == 'league' and data.get('leagues'):
            return data['leagues'][0].get('strBadge')

    except Exception:
        pass
    return None

def fetch_sport_thumb(sport_name):
    """Fetches sport icon from all_sports endpoint"""
    try:
        # V1 Endpoint for sports
        endpoint = f"{TSDB_BASE}/all_sports.php" 
        res = requests.get(endpoint, headers=HEADERS, timeout=5).json()
        if res.get('sports'):
            for s in res['sports']:
                if s.get('strSport') == sport_name:
                    return s.get('strSportIconGreen') or s.get('strSportThumb')
    except: pass
    return None

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
def main():
    # 1. Setup Dirs
    for path in DIRS.values():
        if not os.path.exists(path): os.makedirs(path)

    print("--- 1. Fetching Backend Data ---")
    try:
        data = requests.get(API_URL, headers=HEADERS, timeout=15).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: {e}")
        return

    unique_teams = set()
    unique_leagues = set()
    unique_sports = set()

    for m in matches:
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        
        lg = m.get('tournament') or m.get('league')
        if lg and 'other' not in lg.lower():
            unique_leagues.add(lg)
            
        sp = m.get('sport')
        if sp: unique_sports.add(sp)

    print(f"--- 2. Processing {len(unique_teams)} Teams ---")
    new_count = 0
    
    for raw_name in unique_teams:
        slug = normalize_filename(raw_name)
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching Team: {raw_name} ...")
            # Pass raw_name directly, the function handles cleaning
            url = fetch_logo_v1('team', raw_name)
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_count += 1
            else:
                print(f"     [-] Not Found")
            
            # --- IMPORTANT: V1 Free tier is stricter on rate limits ---
            time.sleep(1.5) 

    print(f"--- 3. Processing {len(unique_leagues)} Leagues ---")
    for raw_name in unique_leagues:
        slug = normalize_filename(raw_name)
        path = os.path.join(DIRS['leagues'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching League: {raw_name} ...")
            url = fetch_logo_v1('league', raw_name)
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
            time.sleep(1.5)

    print(f"--- 4. Processing {len(unique_sports)} Sports ---")
    for sp_slug in unique_sports:
        pretty_name = SPORT_MAPPING.get(sp_slug.lower(), sp_slug.capitalize())
        path = os.path.join(DIRS['sports'], f"{sp_slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching Sport: {pretty_name} ...")
            url = fetch_sport_thumb(pretty_name)
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {sp_slug}.webp")

    print(f"--- DONE. Downloaded {new_count} new logos. ---")

if __name__ == "__main__":
    main()
