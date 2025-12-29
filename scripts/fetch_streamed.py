import os
import requests
import re
import time
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

# REFRESH SETTINGS
REFRESH_DAYS = 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- WHITELIST FOR CLEANING ONLY ---
# We use this list ONLY to remove prefixes from names (e.g. "NBA - Team Name")
# We do NOT use this to stop downloads. We download everything.
ALLOWED_LEAGUES_INPUT = """
NFL, NBA, MLB, NHL, College Football, College-Football, College Basketball, College-Basketball, 
NCAAB, NCAAF, NCAA Men, NCAA-Men, NCAA Women, NCAA-Women, Premier League, Premier-League, 
Champions League, Champions-League, MLS, Bundesliga, Serie-A, Serie A, American-Football, American Football, 
Ice Hockey, Ice-Hockey, Championship, Scottish Premiership, Scottish-Premiership, 
Europa League, Europa-League, A League, A-League, A League Men, A League Women
"""
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

def clean_display_name(name):
    """
    Sanitizer: 
    1. PRIORITY: Colon Rule (Remove "League: " prefix)
    2. FALLBACK: Whitelist prefix removal
    """
    if not name: return None
    
    # --- RULE 1: Generic Colon Stripper ---
    # This ensures "Premier League: Arsenal" becomes "Arsenal"
    if ':' in name:
        parts = name.split(':', 1)
        if len(parts) > 1:
            cleaned = parts[1].strip()
            if cleaned and len(cleaned) > 1:
                return cleaned

    # --- RULE 2: Whitelist Prefix Fallback ---
    # This handles "NBA - Celtics" -> "Celtics"
    lower_name = name.lower()
    for league in VALID_LEAGUES:
        if lower_name.startswith(league):
            remainder = name[len(league):]
            # Remove separator characters (spaces, hyphens)
            clean_remainder = re.sub(r"^[\s-]+", "", remainder)
            if clean_remainder and len(clean_remainder.strip()) > 1:
                return clean_remainder.strip()
                
    return name.strip()

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
    
    print("--- Starting Backend Asset Sync (All Teams) ---")
    
    try:
        data = requests.get(BACKEND_URL, headers=HEADERS).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: Backend unavailable - {e}")
        return

    team_count = 0
    league_count = 0

    for m in matches:
        # Get Raw Data
        home_raw = m.get('home_team')
        away_raw = m.get('away_team')
        league_raw = m.get('league') # We use this only for league images, not filtering
        
        home_imgs = m.get('home_team_image')
        away_imgs = m.get('away_team_image')
        league_imgs = m.get('league_image')

        # ---------------------------
        # PROCESS TEAMS (ALL MATCHES)
        # ---------------------------
        for raw_name, img_obj in [(home_raw, home_imgs), (away_raw, away_imgs)]:
            # 1. Clean Name (Remove prefixes)
            name = clean_display_name(raw_name)
            
            # 2. Slugify
            slug = slugify(name)
            if not slug: continue

            # 3. Download (No restrictions!)
            # Check TSDB first to avoid duplicates/overwriting high-quality images
            tsdb_path = os.path.join(TSDB_DIR, f"{slug}.webp")
            if not os.path.exists(tsdb_path):
                streamed_path = os.path.join(STREAMED_DIR, f"{slug}.webp")
                if img_obj and download_multi_source(img_obj, streamed_path):
                    team_count += 1

        # ---------------------------
        # PROCESS LEAGUE IMAGE
        # ---------------------------
        # We download the league logo if provided, regardless of whitelist
        if league_raw and league_imgs:
            l_slug = slugify(league_raw)
            if l_slug:
                l_path = os.path.join(LEAGUE_DIR, f"{l_slug}.webp")
                if download_multi_source(league_imgs, l_path):
                    league_count += 1

    print(f"--- Sync Done. Teams: {team_count} | Leagues: {league_count} ---")

if __name__ == "__main__":
    main()
