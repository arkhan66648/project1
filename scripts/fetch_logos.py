import os
import requests
import time
import re
from PIL import Image
from io import BytesIO

# ==========================================
# CONFIGURATION
# ==========================================
# Your LIVE Backend URL (The harvester looks at what is currently live/upcoming)
API_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us" 

# Directory Paths
BASE_DIR = 'assets/logos'
DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# TheSportsDB Free API Endpoints
TSDB_SEARCH_TEAM = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
TSDB_SEARCH_LEAGUE = "https://www.thesportsdb.com/api/v1/json/3/searchleagues.php?l="
TSDB_ALL_SPORTS = "https://www.thesportsdb.com/api/v1/json/3/all_sports.php"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def normalize_filename(name):
    """Turns 'Premier League' into 'premier-league' for safe filenames."""
    if not name: return "unknown"
    return re.sub(r'[^a-z0-9]', '-', name.lower().strip())

def save_image_optimized(url, save_path):
    """Downloads, resizes to 60x60 (3x Retina for 20px CSS), and saves as WebP."""
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            
            # Ensure transparency support
            if img.mode != 'RGBA': 
                img = img.convert('RGBA')
            
            # Resize to 60x60 (High Quality for small icons)
            img.thumbnail((60, 60), Image.Resampling.LANCZOS)
            
            # Save as WebP
            img.save(save_path, 'WEBP', quality=90)
            return True
    except Exception as e:
        print(f"    [!] Error processing image: {e}")
    return False

# ==========================================
# SEARCH FUNCTIONS
# ==========================================
def fetch_team_logo(name):
    print(f"  > Searching Team: {name}...")
    try:
        data = requests.get(f"{TSDB_SEARCH_TEAM}{name}", timeout=5).json()
        if data.get('teams'):
            # strTeamBadge is the logo
            return data['teams'][0].get('strTeamBadge')
    except: pass
    return None

def fetch_league_logo(name):
    print(f"  > Searching League: {name}...")
    try:
        data = requests.get(f"{TSDB_SEARCH_LEAGUE}{name}", timeout=5).json()
        if data.get('leagues'):
            # strBadge is the league logo
            return data['leagues'][0].get('strBadge')
    except: pass
    return None

def fetch_sport_logo(name):
    print(f"  > Searching Sport: {name}...")
    # Sports are harder to search, usually we map them manually or iterate all
    # For now, we return None or implement a manual mapping if TSDB fails
    # TSDB 'all_sports.php' lists them, but searching by name is inefficient here.
    # We will skip complex sport search for now to save API calls, 
    # relying on manual upload or 'General' fallback for sports.
    return None 

# ==========================================
# MAIN HARVESTER
# ==========================================
def main():
    # 1. Ensure Directories Exist
    for path in DIRS.values():
        if not os.path.exists(path):
            os.makedirs(path)

    # 2. Get Live Data
    print("--- 1. Fetching Live Match Data ---")
    try:
        data = requests.get(API_URL).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: Failed to connect to backend. {e}")
        return

    # 3. Collect Unique Entities
    unique_teams = set()
    unique_leagues = set()
    unique_sports = set()

    for m in matches:
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        if m.get('league'): unique_leagues.add(m['league'])
        if m.get('tournament'): unique_leagues.add(m['tournament'])
        if m.get('sport'): unique_sports.add(m['sport'])

    print(f"--- Found: {len(unique_teams)} Teams, {len(unique_leagues)} Leagues, {len(unique_sports)} Sports ---")

    # 4. Process Teams
    for team in unique_teams:
        slug = normalize_filename(team)
        path = os.path.join(DIRS['teams'], f"{slug}.webp")
        
        if not os.path.exists(path):
            url = fetch_team_logo(team)
            if url:
                if save_image_optimized(url, path):
                    print(f"    [+] Saved Team: {slug}")
                else:
                    print(f"    [-] Failed to save Team: {slug}")
            time.sleep(0.5) # Be polite to API

    # 5. Process Leagues
    for league in unique_leagues:
        slug = normalize_filename(league)
        path = os.path.join(DIRS['leagues'], f"{slug}.webp")
        
        if not os.path.exists(path):
            url = fetch_league_logo(league)
            if url:
                if save_image_optimized(url, path):
                    print(f"    [+] Saved League: {slug}")
            time.sleep(0.5)

    print("--- Harvester Complete ---")

if __name__ == "__main__":
    main()
