import os
import json
import re

LOGO_DIR = "assets/logos/tsdb"
OUTPUT = "assets/data/image_map.json"

def unslug(slug):
    return " ".join(word.capitalize() for word in slug.split("-"))

map_data = {}

if not os.path.exists(LOGO_DIR):
    print("[!] Logo directory not found.")
else:
    files = os.listdir(LOGO_DIR)
    print(f"--- Map Generator: Found {len(files)} logos ---")

    for file in files:
        name, _ = os.path.splitext(file)
        team_name = unslug(name)
        map_data[team_name] = f"assets/logos/tsdb/{name}"

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

with open(OUTPUT, "w") as f:
    json.dump(map_data, f, indent=2)

print(f"[✓] image_map.json generated with {len(map_data)} entries.")
