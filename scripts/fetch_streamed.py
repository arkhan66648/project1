import os
import requests
import re
import time
from PIL import Image
from io import BytesIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
BACKEND_URL = "https://vercelapi-olive.vercel.app/api/sync-nodes?country=us"
STREAMED_BASE = "https://streamed.pk/api/images/badge/"

TSDB_DIR = "assets/logos/tsdb"
STREAMED_DIR = "assets/logos/streamed"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==========================================
# 2. UTILS
# ==========================================
def slugify(name):
    if not name: return None
    clean = str(name).lower()
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"\s+", "-", clean)
    return clean.strip("-")

def save_image(url, save_path):
    if os.path.exists(save_path): return False
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            if img.mode != 'RGBA': img = img.convert('RGBA')
            img = img.resize((60, 60), Image.Resampling.LANCZOS)
            img.save(save_path, "WEBP", quality=90)
            return True
    except: pass
    return False

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    os.makedirs(STREAMED_DIR, exist_ok=True)
    
    print("--- Starting Gap-Filler Harvester ---")
    
    try:
        data = requests.get(BACKEND_URL, headers=HEADERS).json()
        matches = data.get('matches', [])
    except:
        print("CRITICAL: Backend unavailable")
        return

    # Gather tasks (Team Name -> Badge ID)
    tasks = {}
    for m in matches:
        if m.get('team_a') and m.get('team_a_logo'):
            tasks[m['team_a']] = m['team_a_logo']
        if m.get('team_b') and m.get('team_b_logo'):
            tasks[m['team_b']] = m['team_b_logo']

    count = 0
    for team_name, badge_id in tasks.items():
        slug = slugify(team_name)
        if not slug: continue

        # 1. CHECK TSDB (Priority 1)
        tsdb_path = os.path.join(TSDB_DIR, f"{slug}.webp")
        if os.path.exists(tsdb_path):
            continue # Already have a high-quality logo

        # 2. CHECK STREAMED (Priority 2 - Don't re-download)
        streamed_path = os.path.join(STREAMED_DIR, f"{slug}.webp")
        if os.path.exists(streamed_path):
            continue

        # 3. DOWNLOAD & RENAME
        # If ID contains http, use it, otherwise construct URL
        if "http" in badge_id:
            src_url = badge_id
        else:
            src_url = f"{STREAMED_BASE}{badge_id}.webp"
            
        if save_image(src_url, streamed_path):
            print(f"   [+] Filled Gap: {slug}.webp")
            count += 1
            time.sleep(0.2)

    print(f"--- Done. Filled {count} missing logos. ---")

if __name__ == "__main__":
    main()
