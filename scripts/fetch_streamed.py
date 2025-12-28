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

# STRICT BLOCKLIST (Filter input & clean existing)
GENERIC_SPORTS = {
    "soccer",
  "football",

  "ice hockey", "ice-hockey",
  "field hockey", "field-hockey",

  "cricket",
  "basketball",
  "baseball",

  "rugby",
  "rugby union", "rugby-union",
  "rugby league", "rugby-league",

  "tennis",
  "golf",

  "motorsport", "motorsports",

  "volleyball",
  "handball",

  "table tennis", "table-tennis",
  "badminton",

  "boxing",
  "mma",
  "wrestling",

  "snooker",
  "pool",
  "billiards",
  "darts",

  "cycling",

  "american football", "american-football",
  "aussie rules", "aussie-rules",

  "esports",
  "futsal",
  "netball",

  "kabaddi",
  "athletics",
  "swimming",
  "weightlifting",
  "gymnastics",

  "judo",
  "taekwondo",
  "karate",

  "lacrosse",
  "water polo", "water-polo",
  "softball",
  "floorball",

  "formula 1", "formula-1", "f1",
  "nascar",
  "motogp",

  "skiing",
  "snowboarding",
  "curling",

  "chess"
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
    """Tries multiple sources. Only saves if successful."""
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

    # --- AUTO CLEANER: Remove existing generic sports ---
    cleaned_count = 0
    keys_to_delete = [k for k, v in league_map.items() if str(v).lower().strip() in GENERIC_SPORTS]
    for k in keys_to_delete:
        del league_map[k]
        cleaned_count += 1
    if cleaned_count > 0:
        print(f"--- Purged {cleaned_count} generic entries (e.g., Soccer, Football) from map ---")
    # ----------------------------------------------------

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
        league = m.get('league') # Tournament name OR Generic Sport

        # --- STRICT CHECK: Filter Incoming Data ---
        if league and league.lower().strip() in GENERIC_SPORTS:
            league = None # Ignore this league entirely
        # ------------------------------------------

        home_imgs = m.get('home_team_image')
        away_imgs = m.get('away_team_image')
        league_imgs = m.get('league_image')

        # ---------------------------
        # PROCESS TEAMS
        # ---------------------------
        for name, img_obj in [(home, home_imgs), (away, away_imgs)]:
            slug = slugify(name)
            if not slug: continue

            # A. Update League Map (Priority: Backend)
            # Only update if we have a valid, non-generic league
            if league:
                league_map[slug] = league

            # B. Download Image (Gap Fill)
            tsdb_path = os.path.join(TSDB_DIR, f"{slug}.webp")
            
            if not os.path.exists(tsdb_path):
                streamed_path = os.path.join(STREAMED_DIR, f"{slug}.webp")
                if img_obj and download_multi_source(img_obj, streamed_path):
                    team_count += 1

        # ---------------------------
        # PROCESS LEAGUE IMAGE
        # ---------------------------
        if league and league_imgs:
            l_slug = slugify(league)
            if l_slug:
                l_path = os.path.join(LEAGUE_DIR, f"{l_slug}.webp")
                if download_multi_source(league_imgs, l_path):
                    league_count += 1

    # 2. Save Updated Map
    with open(LEAGUE_MAP_FILE, 'w') as f:
        json.dump(league_map, f, indent=2)

    print(f"--- Sync Done. Teams: {team_count} | Leagues: {league_count} ---")
    print(f"--- League Map Updated: {len(league_map)} items ---")

if __name__ == "__main__":
    main()
