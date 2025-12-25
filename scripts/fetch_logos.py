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

# Directory Setup
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# V2 API BASE URL (Using the structure you provided)
# Note: Usually TSDB requires a key. We assume '3' (Free) or try direct path.
# We will use the standard V1/V2 hybrid path which is most reliable for free tier users:
# https://www.thesportsdb.com/api/v2/json/3/search/team/NAME
TSDB_BASE = "https://www.thesportsdb.com/api/v2/json/3"

# Headers to prevent 403 Forbidden errors
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
    """
    1. Removes prefixes like 'NBA:', 'NHL:', 'Serie A:'.
    2. Removes specific garbage suffixes.
    """
    if not name: return ""
    name = str(name).strip()
    
    # Remove "NBA: ", "NHL: " pattern
    name = re.sub(r'^[A-Za-z0-9\s-]{2,15}:\s*', '', name)
    
    # Remove common suffixes that confuse search
    name = name.replace(" U20", "").replace(" W", "")
    
    return name.strip()

def format_for_v2_api(name):
    """
    V2 requires underscores: 'Los Angeles Lakers' -> 'Los_Angeles_Lakers'
    """
    clean = clean_name(name)
    return re.sub(r'\s+', '_', clean)

def normalize_filename(name):
    """
    Filename safe: 'Los Angeles Lakers' -> 'los-angeles-lakers'
    """
    clean = clean_name(name)
    return re.sub(r'[^a-z0-9]', '-', clean.lower().strip())

# ==========================================
# 3. IMAGE PROCESSING
# ==========================================
def save_image_optimized(url, save_path):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            
            # Convert to RGBA (Transparency)
            if img.mode != 'RGBA': 
                img = img.convert('RGBA')
            
            # Resize to 60x60px (Perfect for 20px CSS display @ 3x Retina)
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception as e:
        # print(f"Img Error: {e}") 
        pass
    return False

# ==========================================
# 4. API FETCHING (V2 STRUCTURE)
# ==========================================
def fetch_logo_v2(category, query_name):
    """
    category: 'team' or 'league'
    query_name: 'Manchester_United' (underscored)
    """
    endpoint = f"{TSDB_BASE}/search/{category}/{query_name}"
    
    try:
        res = requests.get(endpoint, headers=HEADERS, timeout=5)
        if res.status_code != 200: return None
        
        data = res.json()
        
        # Handle TEAM response
        if category == 'team' and data.get('teams'):
            # V2 usually returns a list. Take the first one.
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
        endpoint = f"{TSDB_BASE}/all/sports"
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
        # Collect Teams (Use your specific fields)
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        
        # Collect Leagues
        lg = m.get('tournament') or m.get('league')
        if lg and 'other' not in lg.lower():
            unique_leagues.add(lg)
            
        # Collect Sports
        sp = m.get('sport')
        if sp: unique_sports.add(sp)

    print(f"--- 2. Processing {len(unique_teams)} Teams ---")
    new_count = 0
    
    for raw_name in unique_teams:
        # 1. Prepare names
        v2_query = format_for_v2_api(raw_name)  # e.g. "Charlotte_Hornets"
        slug = normalize_filename(raw_name)     # e.g. "charlotte-hornets"
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        # 2. Check if missing
        if not os.path.exists(path):
            print(f"   > Searching Team: {v2_query} ...")
            url = fetch_logo_v2('team', v2_query)
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
                new_count += 1
            else:
                print(f"     [-] Not Found")
            
            time.sleep(0.2) # Respect API limits

    print(f"--- 3. Processing {len(unique_leagues)} Leagues ---")
    for raw_name in unique_leagues:
        v2_query = format_for_v2_api(raw_name)
        slug = normalize_filename(raw_name)
        path = os.path.join(DIRS['leagues'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > Searching League: {v2_query} ...")
            url = fetch_logo_v2('league', v2_query)
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED: {slug}.webp")
            time.sleep(0.2)

    print(f"--- 4. Processing {len(unique_sports)} Sports ---")
    for sp_slug in unique_sports:
        # Map "basketball" -> "Basketball"
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
