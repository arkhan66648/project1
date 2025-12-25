import os
import json
import requests
from difflib import get_close_matches

BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
DIRS = {'teams': 'assets/logos/teams', 'sports': 'assets/logos/sports'}
OUTPUT_FILE = 'assets/data/image_map.json'

def main():
    if not os.path.exists(DIRS['teams']): os.makedirs(DIRS['teams'])
    
    # Get local files
    local_teams = {f.replace('.webp', ''): f for f in os.listdir(DIRS['teams']) if f.endswith('.webp')}
    print(f"--- Map Generator: Found {len(local_teams)} local team logos ---")

    try:
        data = requests.get(BACKEND_URL).json()
        matches = data.get('matches', [])
    except:
        return

    image_map = {"teams": {}, "sports": {}}
    team_keys = list(local_teams.keys())

    for m in matches:
        for t in ['team_a', 'team_b']:
            name = m.get(t)
            if not name: continue
            
            # Normalize
            target = "".join([c for c in name.lower() if c.isalnum()])
            
            # Match
            match = get_close_matches(target, team_keys, n=1, cutoff=0.6)
            if match:
                image_map["teams"][name] = local_teams[match[0]]

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(image_map, f, indent=2)
    print("--- Map Saved ---")

if __name__ == "__main__":
    main()
