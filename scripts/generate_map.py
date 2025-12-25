import os
import json
import requests
from difflib import get_close_matches

BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
TEAMS_DIR = "assets/logos/teams"
OUTPUT_FILE = "assets/data/image_map.json"

def normalize(name):
    return "".join(c for c in name.lower() if c.isalnum())

def main():
    os.makedirs(TEAMS_DIR, exist_ok=True)

    local_files = {
        f.replace(".webp", ""): f
        for f in os.listdir(TEAMS_DIR)
        if f.endswith(".webp")
    }

    print(f"--- Map Generator: Found {len(local_files)} local team logos ---")

    if not local_files:
        print("[!] No logos found. Map will be empty.")
        return

    try:
        data = requests.get(BACKEND_URL, timeout=15).json()
        matches = data.get("matches", [])
    except:
        print("[!] Failed to fetch backend data.")
        return

    image_map = {"teams": {}}
    local_keys = list(local_files.keys())

    for match in matches:
        for side in ["team_a", "team_b"]:
            name = match.get(side)
            if not name:
                continue

            key = normalize(name)
            found = get_close_matches(key, local_keys, n=1, cutoff=0.6)

            if found:
                image_map["teams"][name] = local_files[found[0]]

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(image_map, f, indent=2)

    print("--- Map Saved Successfully ---")

if __name__ == "__main__":
    main()
