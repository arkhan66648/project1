import os
import json
import re
import shutil

# ==========================================
# 1. CONFIGURATION
# ==========================================
DIRS = {
    'streamed': 'assets/logos/streamed',
    'league_map': 'assets/data/league_map.json',
    'image_map': 'assets/data/image_map.json'
}

# Same Whitelist as your other scripts
ALLOWED_LEAGUES_INPUT = """
NFL, NBA, MLB, NHL, College Football, College-Football, College Basketball, College-Basketball, 
NCAAB, NCAAF, NCAA Men, NCAA-Men, NCAA Women, NCAA-Women, Premier League, Premier-League, 
Champions League, Champions-League, MLS, Bundesliga, Serie-A, Serie A, American-Football, American Football, 
Ice Hockey, Ice-Hockey, Championship, Scottish Premiership, Scottish-Premiership, A League Women, A League Men, 
Europa League, Europa-League, A League, A League Women, A League Men, A-League, A-League-Men, A-League-Women, africa-cup-of-nations, Africa cup of nations, cambodia-tour-of-Indonesia, Cambodia tour of Indonesia, england-tour-of-Australia, England tour of Australia, euroleague, g-league, g league, jupiler-pro-league, jupiler pro league, myanmar-tour-of-Bhutan, Myanmar tour of Bhutan, nba-g-league
"""
# Set of lowercased allowed names
VALID_LEAGUES = {x.strip().lower() for x in ALLOWED_LEAGUES_INPUT.split(',') if x.strip()}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def slugify(name):
    if not name: return None
    clean = str(name).lower()
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"\s+", "-", clean)
    return clean.strip("-")

def get_league_slugs():
    """Returns a list of slugified league names for checking file prefixes."""
    # 1. Generate slugs
    slugs = [slugify(l) for l in VALID_LEAGUES if l and l.strip()]
    # 2. Remove duplicates (sets are unordered)
    slugs = list(set(slugs))
    # 3. CRITICAL FIX: Sort by length descending.
    # Checks "a-league-women" (longer) before "a-league" (shorter)
    slugs.sort(key=len, reverse=True)
    return slugs

def clean_filename_slug(slug, league_slugs):
    """
    Input: 'nba-boston-celtics'
    Output: 'boston-celtics' (if 'nba' is in league_slugs)
    """
    for l_slug in league_slugs:
        # Check for 'league-' prefix
        prefix = f"{l_slug}-"
        if slug.startswith(prefix):
            return slug[len(prefix):] # Remove prefix
    return slug

def clean_display_name(name):
    """
    Input: 'Premier League: Manchester United'
    Output: 'Manchester United'
    """
    if not name: return name
    lower_name = name.lower()
    
    for league in VALID_LEAGUES:
        # Check for 'League Name:' or 'League Name ' at start
        if lower_name.startswith(league.lower()): 
            remainder = name[len(league):]
            # Strip separators
            clean_remainder = re.sub(r"^[:\s-]+", "", remainder) 
            
            if clean_remainder and len(clean_remainder.strip()) > 1: 
                return clean_remainder.strip() 

    return name.strip() 

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    print("--- Starting SAFE Cleanup ---")
    
    # Pre-calc league slugs (Now sorted!)
    league_slugs = get_league_slugs()

    # -------------------------------------------------
    # STEP A: Fix Files in 'assets/logos/streamed'
    # -------------------------------------------------
    print("\n[1/3] Checking Filesystem...")
    if os.path.exists(DIRS['streamed']):
        renamed_count = 0
        deleted_count = 0
        
        for filename in os.listdir(DIRS['streamed']):
            if not filename.endswith(".webp"): continue
            
            old_slug = filename.replace(".webp", "")
            new_slug = clean_filename_slug(old_slug, league_slugs)
            
            if new_slug != old_slug:
                old_path = os.path.join(DIRS['streamed'], filename)
                new_path = os.path.join(DIRS['streamed'], f"{new_slug}.webp")
                
                if os.path.exists(new_path):
                    # Collision! The clean file already exists.
                    os.remove(old_path)
                    deleted_count += 1
                    print(f"  [DEL] Duplicate merged: {filename} -> (kept existing) {new_slug}.webp")
                else:
                    # Rename
                    os.rename(old_path, new_path)
                    renamed_count += 1
                    print(f"  [MOV] Renamed: {filename} -> {new_slug}.webp")
        
        print(f"   > Files Renamed: {renamed_count}")
        print(f"   > Duplicates Removed: {deleted_count}")

    # -------------------------------------------------
    # STEP B: Fix 'league_map.json'
    # -------------------------------------------------
    print("\n[2/3] Fixing League Map...")
    if os.path.exists(DIRS['league_map']):
        try:
            shutil.copy(DIRS['league_map'], DIRS['league_map'] + ".bak")
        except: pass
        
        try:
            with open(DIRS['league_map'], 'r') as f:
                old_map = json.load(f)
            
            new_map = {}
            cleaned_keys = 0
            
            for k, v in old_map.items():
                clean_key = clean_filename_slug(k, league_slugs)
                new_map[clean_key] = v
                if clean_key != k:
                    cleaned_keys += 1
                    
            with open(DIRS['league_map'], 'w') as f:
                json.dump(new_map, f, indent=2)
                
            print(f"   > Map Entries Cleaned: {cleaned_keys}")
        except Exception as e:
            print(f"   [!] Error processing {DIRS['league_map']}: {e}")

    # -------------------------------------------------
    # STEP C: Fix 'image_map.json'
    # -------------------------------------------------
    print("\n[3/3] Fixing Image Map...")
    if os.path.exists(DIRS['image_map']):
        try:
            shutil.copy(DIRS['image_map'], DIRS['image_map'] + ".bak")
        except: pass

        try:
            with open(DIRS['image_map'], 'r') as f:
                img_data = json.load(f)
                
            teams_data = img_data.get('teams', {})
            new_teams_data = {}
            img_map_fixes = 0
            
            for name, path in teams_data.items():
                # 1. Clean the Display Name
                clean_name_key = clean_display_name(name)
                
                # 2. Clean the File Path
                clean_path_val = path
                path_parts = path.split('/')
                if path_parts:
                    filename = path_parts[-1]
                    if filename.endswith('.webp'):
                        file_slug = filename.replace('.webp', '')
                        # This checks against the sorted list now
                        clean_file_slug = clean_filename_slug(file_slug, league_slugs)
                        path_parts[-1] = f"{clean_file_slug}.webp"
                        clean_path_val = "/".join(path_parts)
                
                new_teams_data[clean_name_key] = clean_path_val
                
                if clean_name_key != name or clean_path_val != path:
                    img_map_fixes += 1

            img_data['teams'] = new_teams_data
            
            with open(DIRS['image_map'], 'w') as f:
                json.dump(img_data, f, indent=2)
                
            print(f"   > Image Map Entries Fixed: {img_map_fixes}")
        except Exception as e:
            print(f"   [!] Error processing {DIRS['image_map']}: {e}")

    print("\n--- Cleanup Complete ---")

if __name__ == "__main__":
    main()
