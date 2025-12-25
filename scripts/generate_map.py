import os
import json
import requests
from difflib import get_close_matches

# ==========================================
# 1. CONFIGURATION
# ==========================================
BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
BASE_DIR = 'assets/logos'
OUTPUT_FILE = 'assets/data/image_map.json'

DIRS = {
    'teams': os.path.join(BASE_DIR, 'teams'),
    'leagues': os.path.join(BASE_DIR, 'leagues'),
    'sports': os.path.join(BASE_DIR, 'sports')
}

# ==========================================
# 2. UTILS
# ==========================================
def normalize_key(name):
    """
    Simplifies backend names for better matching
    'Man City' -> 'man-city'
    """
    if not name: return ""
    clean = str(name).lower().replace(" fc", "").replace(" united", "").replace(" city", "")
    return "".join([c for c in clean if c.isalnum() or c == '-']).strip()

def main():
    print("--- 1. Loading Local Assets ---")
    
    # Load available files (stripping .webp extension)
    available_teams = {f.replace('.webp', ''): f for f in os.listdir(DIRS['teams']) if f.endswith('.webp')}
    available_sports = {f.replace('.webp', ''): f for f in os.listdir(DIRS['sports']) if f.endswith('.webp')}

    print(f"Local Library: {len(available_teams)} Teams, {len(available_sports)} Sports.")

    print("--- 2. Fetching Backend Data ---")
    try:
        data = requests.get(BACKEND_URL).json()
        matches = data.get('matches', [])
    except Exception as e:
        print(f"CRITICAL: Could not fetch backend. {e}")
        return

    # Extract unique names from backend
    unique_teams = set()
    unique_sports = set()

    for m in matches:
        if m.get('team_a'): unique_teams.add(m['team_a'])
        if m.get('team_b'): unique_teams.add(m['team_b'])
        if m.get('sport'): unique_sports.add(m['sport'])

    # Initialize Map Structure
    image_map = {
        "teams": {},
        "sports": {}
    }

    print(f"--- 3. Mapping {len(unique_teams)} Teams ---")
    
    # Prepare keys for fuzzy matching
    team_keys = list(available_teams.keys())
    
    for backend_name in unique_teams:
        # Create a slug from backend name
        search_slug = "".join([c for c in backend_name.lower() if c.isalnum() or c == '-'])
        
        match_found = None
        
        # A. Exact Slug Match (Fastest)
        if search_slug in available_teams:
            match_found = available_teams[search_slug]
        
        # B. Fuzzy Match (Slower, but handles "Man City" vs "Manchester City")
        else:
            norm_search = normalize_key(backend_name)
            # cutoff=0.6 means 60% similarity required
            matches = get_close_matches(norm_search, team_keys, n=1, cutoff=0.6)
            if matches:
                match_found = available_teams[matches[0]]

        if match_found:
            image_map["teams"][backend_name] = match_found

    # --- SPORT MAPPING ---
    print(f"--- 4. Mapping Sports ---")
    for sp in unique_sports:
        slug = sp.lower()
        if slug in available_sports:
            image_map["sports"][sp] = available_sports[slug]

    # --- SAVE JSON ---
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(image_map, f, indent=2)

    print(f"--- DONE. Map saved to {OUTPUT_FILE} ---")

if __name__ == "__main__":
    main()
