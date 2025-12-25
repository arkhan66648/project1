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
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

# Directory Setup
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# Real Browser Headers (Helps avoid 403 Forbidden)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.thesportsdb.com/'
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    clean = str(name).strip().replace("_", " ")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def save_image_optimized(url, save_path):
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
# 3. API FETCHING WITH DEBUGGING
# ==========================================
def fetch_logo_v1(category, raw_name):
    clean_name = raw_name.replace("_", " ").strip()
    encoded_name = urllib.parse.quote(clean_name)
    
    endpoint = ""
    if category == 'team':
        endpoint = f"{TSDB_BASE}/searchteams.php?t={encoded_name}"
    elif category == 'league':
        endpoint = f"{TSDB_BASE}/searchleague.php?l={encoded_name}"
        
    try:
        res = requests.get(endpoint, headers=HEADERS, timeout=10)
        
        # --- DEBUGGING BLOCK ---
        if res.status_code != 200:
            print(f"     [!] API Error {res.status_code}: {endpoint}")
            return None
        
        data = res.json()
        
        # Check if data is null (common with free key if no match found)
        if data is None:
            return None

        if category == 'team' and data.get('teams'):
            return data['teams'][0].get('strTeamBadge')
        elif category == 'league' and data.get('leagues'):
            return data['leagues'][0].get('strBadge')

    except Exception as e:
        print(f"     [!] Exception: {e}")
        pass
    return None

def fetch_sport_thumb(sport_name):
    try:
        endpoint = f"{TSDB_BASE}/all_sports.php"
        res = requests.get(endpoint, headers=HEADERS, timeout=10).json()
        if res.get('sports'):
            for s in res['sports']:
                if s.get('strSport') == sport_name:
                    return s.get('strSportIconGreen') or s.get('strSportThumb')
    except: pass
    return None

# ==========================================
# 4. MAIN
# ==========================================
def main():
    # TEST CONNECTION FIRST
    print("--- 0. Testing API Connection (Arsenal) ---")
    test_url = f"{TSDB_BASE}/searchteams.php?t=Arsenal"
    test_res = requests.get(test_url, headers=HEADERS)
    print(f"Test Status: {test_res.status_code}")
    if test_res.status_code != 200:
        print(f"CRITICAL: API blocked you. Response: {test_res.text[:100]}")
        return

    # Create Dirs
    for path in DIRS.values():
        if not os.path.exists(path): os.makedirs(path)

    print("--- 1. Fetching Backend Data ---")
    try:
        data = requests.get(API_URL, headers=HEADERS, timeout=15).json()
        matches = data.get('matches', [])
    except:
        return

    unique_teams = set()
    for m in matches:
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])

    print(f"--- 2. Processing {len(unique_teams)} Teams ---")
    
    for i, raw_name in enumerate(unique_teams):
        slug = normalize_filename(raw_name)
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        if not os.path.exists(path):
            print(f"   > [{i}/{len(unique_teams)}] Searching: {raw_name}")
            url = fetch_logo_v1('team', raw_name)
            
            if url and save_image_optimized(url, path):
                print(f"     [+] SAVED")
            else:
                print(f"     [-] Not Found / Null Response")
            
            # SLOW DOWN to prevent 429 Rate Limit (Free Tier = ~25 req/min)
            time.sleep(2.5) 

if __name__ == "__main__":
    main()
