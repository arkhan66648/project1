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

def normalize(name):
    if not name: return ""
    return "".join([c for c in name.lower() if c.isalnum()])

def main():
    # 1. Index Local Files
    team_paths = {}   
    league_paths = {} 

    # Load TSDB (Priority 1 for Teams)
    if os.path.exists(DIRS['tsdb']):
        for f in os.listdir(DIRS['tsdb']):
            if f.endswith('.webp'):
                team_paths[f.replace('.webp', '')] = f"/{DIRS['tsdb']}/{f}"

    # Load Streamed (Priority 2 for Teams)
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

    print(f"--- Map Gen: {len(team_paths)} Teams, {len(league_paths)} Leagues Indexed ---")

    # 2. Fetch Backend Matches
    try:
        data = requests.get(BACKEND_URL).json()
        matches = data.get('matches', [])
    except:
        matches = []

    # 3. Create Frontend Map
    # Structure: { "teams": { "Arsenal": "/path..." }, "leagues": { "EPL": "/path..." } }
    final_teams = {}
    final_leagues = {}
    
    avail_teams = list(team_paths.keys())
    avail_leagues = list(league_paths.keys())

    for m in matches:
        # Map Teams
        for t_key in ['home_team', 'away_team']:
            team_name = m.get(t_key)
            if not team_name: continue
            
            slug = "".join([c for c in team_name.lower() if c.isalnum() or c == '-']).strip('-')
            
            # Find Image Path
            if slug in team_paths:
                final_teams[team_name] = team_paths[slug]
            else:
                fuzzy = get_close_matches(slug, avail_teams, n=1, cutoff=0.75)
                if fuzzy:
                    final_teams[team_name] = team_paths[fuzzy[0]]

        # Map Leagues
        league_name = m.get('league')
        if league_name:
            slug = "".join([c for c in league_name.lower() if c.isalnum() or c == '-']).strip('-')
            
            if slug in league_paths:
                final_leagues[league_name] = league_paths[slug]
            else:
                fuzzy = get_close_matches(slug, avail_leagues, n=1, cutoff=0.7)
                if fuzzy:
                    final_leagues[league_name] = league_paths[fuzzy[0]]

    # 4. Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({ "teams": final_teams, "leagues": final_leagues }, f, indent=2)
        
    print(f"--- Map Saved: {len(final_teams)} Teams, {len(final_leagues)} Leagues ---")

if __name__ == "__main__":
    main()
