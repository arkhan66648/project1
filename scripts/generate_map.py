import os
import json

LOGO_DIR = "assets/logos"
OUTPUT = "logo-map.json"

map_data = {}

if not os.path.exists(LOGO_DIR):
    print("[!] Logo directory not found.")
else:
    files = os.listdir(LOGO_DIR)
    print(f"--- Map Generator: Found {len(files)} local team logos ---")

    for file in files:
        team = file.rsplit(".", 1)[0]
        map_data[team] = f"/assets/logos/{file}"

with open(OUTPUT, "w") as f:
    json.dump(map_data, f, indent=2)

if not map_data:
    print("[!] No logos found. Map will be empty.")
else:
    print(f"[✓] logo-map.json generated with {len(map_data)} entries.")
