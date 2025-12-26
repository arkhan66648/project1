import os
import json

LOGO_DIR = "assets/logos/tsdb"
OUTPUT = "assets/data/image_map.json"

def unslug(slug):
    return " ".join(word.capitalize() for word in slug.split("-"))

map_data = {}

if not os.path.exists(LOGO_DIR):
    print("[!] Logo directory not found.")
else:
    files = [f for f in os.listdir(LOGO_DIR) if f.endswith(".webp")]
    print(f"--- Map Generator: Found {len(files)} logos ---")

    for file in files:
        slug = file.replace(".webp", "")
        team_name = unslug(slug)
        map_data[team_name] = f"assets/logos/tsdb/{slug}"

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

with open(OUTPUT, "w") as f:
    json.dump(map_data, f, indent=2)

print(f"[✓] image_map.json generated with {len(map_data)} entries.")
