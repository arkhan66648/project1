import os
import requests
import re
import time
import json
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
STREAMED_HASH_BASE = "https://streamed.pk/api/images/badge/"

# Directories
TSDB_DIR = "assets/logos/tsdb"
STREAMED_DIR = "assets/logos/streamed"
LEAGUE_DIR = "assets/logos/leagues"
LEAGUE_MAP_FILE = "assets/data/league_map.json"
REFRESH_DAYS = 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- WHITELIST CONFIGURATION ---
ALLOWED_LEAGUES_INPUT = """
NFL, NBA, MLB, NHL, College Football, College-Football, College Basketball, College-Basketball, 
NCAAB, NCAAF, NCAA Men, NCAA-Men, NCAA Women, NCAA-Women, Premier League, Premier-League, 
Champions League, Champions-League, MLS, Bundesliga, Serie-A, Serie A, American Football, 
Ice Hockey, Ice-Hockey, Championship, Scottish Premiership, Scottish-Premiership, 
Europa League, Europa-League
"""
# Set of lowercased allowed names
VALID_LEAGUES = {x.strip().lower() for x in ALLOWED_LEAGUES_INPUT.split(',') if x.strip()}

# ==========================================
# 2. UTILS
# ==========================================
def slugify(name):
    if not name: return None
    clean = str(name).lower()
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"\s+", "-", clean)
    return clean.strip("-")

def resolve_url(source_val):
    if not source_val: return None
    if source_val.startswith("http"):
        return source_val
    return f"{STREAMED_HASH_BASE}{source_val}.webp"

def should_download(path):
    if not os.path.exists(path): return True
    file_age_days = (time.time() - os.path.getmtime(path)) / (24 * 3600)
    return file_age_days > REFRESH_DAYS

def download_multi_source(source_obj, save_path):
    if not should_download(save_path): return False
    
    urls = []
    if isinstance(source_obj, dict):
        urls = list(source_obj.values())
    elif isinstance(source_obj, list):
        urls = source_obj
    elif isinstance(source_obj, str):
        urls = [source_obj]

    for raw_url in urls:
        final_url = resolve_url(raw_url)
        if not final_url: continue

        try:
            resp = requests.get(final_url, headers=HEADERS, timeout=8)
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
            continue
    return False

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    os.makedirs(STREAMED_DIR, exist_ok=True)
    os.makedirs(LEAGUE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LEAGUE_MAP_FILE), exist_ok=True)

    # 1. Load Map
    league_map = {}
    if os.path.exists(LEAGUE_MAP_FILE):
        try:
            with open(LEAGUE_MAP_FILE, 'r') as f:
                league_map = json.load(f)
        except: pass

    # 2. CLEAN UP: Remove entries not in VALID_LEAGUES
    # This ensures we delete teams whose league is generic or not in our new whitelist
    cleaned_count = 0
    keys_to_delete = [
        k for k, v in league_map.items() 
        if str(v).lower().strip() not in VALID_LEAGUES
    ]
    for k in keys_to_delete:
        del league_map[k]
        cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"--- Auto-Cleaned {cleaned_count} items not in Whitelist ---")

    print("--- Starting Backend Asset Sync ---")
    
    try:
        data = requests.get(BACKEND_URL, headers=HEADERS).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: Backend unavailable - {e}")
        return

    team_count = 0
    league_count = 0

    for m in matches:
        home = m.get('home_team')
        away = m.get('away_team')
        league = m.get('league') # Can be None, Generic, or Valid
        
        home_imgs = m.get('home_team_image')
        away_imgs = m.get('away_team_image')
        league_imgs = m.get('league_image')

        # Check if incoming league is valid
        is_valid_league = False
        if league and league.strip().lower() in VALID_LEAGUES:
            is_valid_league = True

        # ---------------------------
        # PROCESS TEAMS
        # ---------------------------
        for name, img_obj in [(home, home_imgs), (away, away_imgs)]:
            slug = slugify(name)
            if not slug: continue

            # LOGIC:
            # 1. If incoming league is VALID, update map (Priority: New Data)
            # 2. If incoming league is INVALID/MISSING, check if we already have it in map.
            # 3. If neither, we DO NOT add it to the map (Strict Whitelist).

            if is_valid_league:
                league_map[slug] = league # Update with fresh valid data
            
            # Decide if we download the image:
            # We download if we have a valid league recorded (either just now or previously)
            if slug in league_map:
                # Check TSDB first
                tsdb_path = os.path.join(TSDB_DIR, f"{slug}.webp")
                if not os.path.exists(tsdb_path):
                    streamed_path = os.path.join(STREAMED_DIR, f"{slug}.webp")
                    if img_obj and download_multi_source(img_obj, streamed_path):
                        team_count += 1

        # ---------------------------
        # PROCESS LEAGUE IMAGE
        # ---------------------------
        if is_valid_league and league_imgs:
            l_slug = slugify(league)
            if l_slug:
                l_path = os.path.join(LEAGUE_DIR, f"{l_slug}.webp")
                if download_multi_source(league_imgs, l_path):
                    league_count += 1

    # 3. Save Updated Map
    with open(LEAGUE_MAP_FILE, 'w') as f:
        json.dump(league_map, f, indent=2)

    print(f"--- Sync Done. Teams: {team_count} | Leagues: {league_count} ---")
    print(f"--- League Map Updated: {len(league_map)} items ---")

if __name__ == "__main__":
    main()
