import os
import requests
import time
import urllib.parse
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# TARGET LEAGUES: The specific leagues you want to harvest logos for.
# Map = "Name in your Backend/Common Name": "Official TSDB Name"
TARGET_LEAGUES = {
    # Soccer
    "Premier League": "English Premier League",
    "Championship": "English League Championship",
    "La Liga": "Spanish La Liga",
    "Bundesliga": "German Bundesliga",
    "Serie A": "Italian Serie A",
    "Ligue 1": "French Ligue 1",
    "Eredivisie": "Dutch Eredivisie",
    "Primeira Liga": "Portuguese Primeira Liga",
    "Champions League": "UEFA Champions League",
    "Europa League": "UEFA Europa League",
    "MLS": "American Major League Soccer",
    "Saudi Pro League": "Saudi Arabian Pro League",
    "Saudi Premier League": "Saudi Arabian Pro League", 
    "Belgian Pro League": "Belgian Jupiler League",
    
    # US Sports
    "NBA": "NBA",
    "NFL": "NFL",
    "NHL": "NHL",
    "MLB": "Major League Baseball",
    "NCAA Football": "NCAA Division 1",
    "NCAA Basketball": "NCAA Division I Basketball",
    
    # Others
    "F1": "Formula 1",
    "UFC": "UFC",
    "Big Bash League": "Australian Big Bash League",
    "SA20": "South African SA20",
    "United Rugby Championship": "United Rugby Championship",
    "Top 14": "French Top 14",
    "Premiership Rugby": "English Premiership Rugby"
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_filename(name):
    """Clean filename: 'Man City' -> 'man-city'"""
    clean = str(name).strip().replace("_", " ").replace(".", "")
    return "".join([c for c in clean.lower() if c.isalnum() or c == '-']).strip()

def process_and_save_image(url, save_path):
    """Downloads, Resizes to 60x60, Converts to WEBP"""
    if os.path.exists(save_path): return False # Skip if exists
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            
            # Convert to RGBA (Transparency)
            if img.mode != 'RGBA': 
                img = img.convert('RGBA')
            
            # Resize to exactly 60x60 (High Quality Downsampling)
            img = img.resize((60, 60), Image.Resampling.LANCZOS)
            
            # Save as WEBP
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception:
        pass
    return False

# ==========================================
# 3. HARVESTERS
# ==========================================
def fetch_sports_logos():
    print(" > Fetching Sport Icons...")
    try:
        data = requests.get(f"{TSDB_BASE}/all_sports.php", headers=HEADERS).json()
        if data.get('sports'):
            for s in data['sports']:
                name = s['strSport']
                url = s.get('strSportIconGreen') or s.get('strSportThumb')
                if url:
                    path = os.path.join(DIRS['sports'], f"{normalize_filename(name)}.webp")
                    process_and_save_image(url, path)
    except: pass

def fetch_league_and_teams(common_name, tsdb_name):
    print(f" > Processing: {tsdb_name}...")
    
    encoded = urllib.parse.quote(tsdb_name)
    # 1. Get Teams (search_all_teams.php returns teams AND league badge often)
    url = f"{TSDB_BASE}/search_all_teams.php?l={encoded}"
    
    try:
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        
        # A. Save League Badge (if we can find it separately, otherwise skip)
        # TSDB V1 is tricky with league badges in the team response. 
        # We will try a separate lightweight call for league badge if needed, 
        # but let's stick to teams first to save API calls.
        
        # B. Save Team Badges
        if data and data.get('teams'):
            count = 0
            for t in data['teams']:
                team_name = t['strTeam']
                badge_url = t['strTeamBadge']
                
                if badge_url:
                    slug = normalize_filename(team_name)
                    path = os.path.join(DIRS['teams'], f"{slug}.webp")
                    if process_and_save_image(badge_url, path):
                        count += 1
                        
                    # Also save Alternate names if present
                    if t.get('strAlternate'):
                        slug_alt = normalize_filename(t['strAlternate'])
                        path_alt = os.path.join(DIRS['teams'], f"{slug_alt}.webp")
                        process_and_save_image(badge_url, path_alt)

            print(f"   [+] Saved {count} new team logos.")
        else:
            print(f"   [-] No teams found.")

    except Exception as e:
        print(f"   [!] Error: {e}")

# ==========================================
# 4. MAIN
# ==========================================
def main():
    # Setup Directories
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)

    print("--- 1. Harvesting Sports ---")
    fetch_sports_logos()

    print("--- 2. Harvesting Leagues & Teams ---")
    for common, tsdb in TARGET_LEAGUES.items():
        fetch_league_and_teams(common, tsdb)
        time.sleep(1.5) # Rate limit protection

if __name__ == "__main__":
    main()
