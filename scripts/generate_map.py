import os
import json
import requests
from difflib import get_close_matches

# CONFIG
BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
DIRS = {
    'tsdb': 'assets/logos/tsdb',
    'streamed': 'assets/logos/streamed',
    'leagues': 'assets/logos/leagues'
}
OUTPUT_FILE = 'assets/data/image_map.json'
FUZZY_CUTOFF = 0.85 

# --- WHITELIST CONFIGURATION ---
ALLOWED_LEAGUES_INPUT = """
NFL, NBA, MLB, NHL, College Football, College-Football, College Basketball, College-Basketball, 
NCAAB, NCAAF, NCAA Men, NCAA-Men, NCAA Women, NCAA-Women, Premier League, Premier-League, 
Champions League, Champions-League, MLS, Bundesliga, Serie-A, Serie A, American Football, 
Ice Hockey, Ice-Hockey, Championship, Scottish Premiership, Scottish-Premiership, 
Europa League, Europa-League
"""
VALID_LEAGUES = {x.strip().lower() for x in ALLOWED_LEAGUES_INPUT.split(',') if x.strip()}

def main():
    print("--- Generating Image Map ---")

    # 1. Index Local Files
    team_paths = {}   
    league_paths = {} 

    # Load TSDB (Priority 1)
    if os.path.exists(DIRS['tsdb']):
        for f in os.listdir(DIRS['tsdb']):
            if f.endswith('.webp'):
                team_paths[f.replace('.webp', '')] = f"/{DIRS['tsdb']}/{f}"

    # Load Streamed (Priority 2)
    if os.path.exists(DIRS['streamed']):
        for f in os.listdir(DIRS['streamed']):
            if f.endswith('.webp'):
                slug = f.replace('.webp', '')
                if slug not in team_paths:
                    team_paths[slug] = f"/{DIRS['streamed']}/{f}"

    # Load Leagues
    if os.path.exists(DIRS['leagues']):
        for f in os.listdir(DIRS['leagues']):
            if f.endswith('.webp'):
                slug = f.replace('.webp', '')
                league_paths[slug] = f"/{DIRS['leagues']}/{f}"

    # 2. Fetch Backend Matches
    try:
        data = requests.get(BACKEND_URL).json()
        matches = data.get('matches', [])
    except:
        matches = []

    # 3. Create Frontend Map
    final_teams = {}
    final_leagues = {}
    
    avail_teams = list(team_paths.keys())
    avail_leagues = list(league_paths.keys())

    for m in matches:
        league_name = m.get('league')
        
        # --- STRICT CHECK: Skip if league is not in Whitelist ---
        # This prevents generic "Soccer" or "Football" from grouping teams in the output
        if not league_name or league_name.strip().lower() not in VALID_LEAGUES:
            continue
        # --------------------------------------------------------

        # Map Teams
        for t_key in ['home_team', 'away_team']:
            team_name = m.get(t_key)
            if not team_name: continue
            
            slug = "".join([c for c in team_name.lower() if c.isalnum() or c == '-']).strip('-')
            
            if slug in team_paths:
                final_teams[team_name] = team_paths[slug]
            else:
                fuzzy = get_close_matches(slug, avail_teams, n=1, cutoff=FUZZY_CUTOFF)
                if fuzzy:
                    final_teams[team_name] = team_paths[fuzzy[0]]

        # Map League
        if league_name:
            slug = "".join([c for c in league_name.lower() if c.isalnum() or c == '-']).strip('-')
            
            if slug in league_paths:
                final_leagues[league_name] = league_paths[slug]
            else:
                fuzzy = get_close_matches(slug, avail_leagues, n=1, cutoff=FUZZY_CUTOFF)
                if fuzzy:
                    final_leagues[league_name] = league_paths[fuzzy[0]]

    # 4. Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({ "teams": final_teams, "leagues": final_leagues }, f, indent=2)
        
    print(f"--- Map Saved: {len(final_teams)} Teams, {len(final_leagues)} Leagues ---")

if __name__ == "__main__":
    main()
