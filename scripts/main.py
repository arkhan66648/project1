import json
import time
import requests
import os
import base64
import shutil
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================

# 1. League Detection / Keywords
LEAGUE_KEYWORDS = {
    "NFL": ["NFL", "Super Bowl", "American Football"],
    "NBA": ["NBA", "Basketball", "Playoffs"],
    "NHL": ["NHL", "Ice Hockey", "Stanley Cup"],
    "MLB": ["MLB", "Baseball"],
    "UFC": ["UFC", "MMA", "Fighting", "Fight Night", "Bellator"],
    "F1": ["Formula 1", "F1", "Grand Prix"],
    "Boxing": ["Boxing", "Fight"],
    "Soccer": ["Soccer", "Premier League", "Champions League", "La Liga", "MLS", "Bundesliga"]
}

# 2. Priority Settings (USA Focus)
USA_TARGETS = ["NFL", "NBA", "UFC", "NHL", "MLB"]
NOW_MS = int(time.time() * 1000)

def load_config():
    with open('data/config.json', 'r') as f:
        return json.load(f)

# ==========================================
# HELPER: ENCRYPTION (BASE64)
# ==========================================
def obfuscate_link(link):
    """
    Takes a raw URL (e.g., https://stream.com/live)
    Returns Base64 String (e.g., aHR0cHM6Ly9zdHJlYW0uY29tL2xpdmU=)
    """
    if not link: return ""
    # Convert string to bytes, encode, then back to string
    return base64.b64encode(link.encode('utf-8')).decode('utf-8')

def detect_league(category, title):
    text = (str(category) + " " + str(title)).upper()
    
    for league, keywords in LEAGUE_KEYWORDS.items():
        for k in keywords:
            if k.upper() in text:
                if category == "American Football": return "NFL" 
                if category == "Basketball": return "NBA"
                if category in ["Fighting", "MMA"]: return "UFC"
                return league
    return category

# ==========================================
# FETCHING DATA
# ==========================================

def fetch_streamed_pk(url):
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        for m in data:
            title = m.get('title', 'Unknown Match')
            raw_cat = m.get('category', 'Other')
            league = detect_league(raw_cat, title)
            
            # Process Streams: Encode them immediately
            processed_streams = []
            for src in m.get('sources', []):
                # Streamed.pk often gives an ID or a direct link. 
                # We assume 'id' or 'url' is the stream target.
                raw_link = src.get('url') or src.get('id') or ""
                processed_streams.append({
                    "source": src.get('source', 'streamed'),
                    "id": obfuscate_link(str(raw_link)), # ENCODING APPLIED HERE
                    "resolution": "HD"
                })

            matches.append({
                "id": str(m['id']),
                "title": title,
                "sport": league,
                "start_time": m['date'], # Already in MS
                "viewers": m.get('viewers', 0),
                "streams": processed_streams,
                "teams": m.get('teams', {}),
                "image": f"https://streamed.pk/api/images/poster/{m['teams']['home']['badge']}/{m['teams']['away']['badge']}.webp" if m.get('teams') else "assets/fallback.jpg",
                "origin": "streamed"
            })
        return matches
    except Exception as e:
        print(f"Error fetching Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        # TopEmbed structure: events -> "date" -> [list]
        for date_key, events in data.get('events', {}).items():
            for ev in events:
                start_ms = int(ev['unix_timestamp']) * 1000
                league = detect_league(ev.get('sport', ''), ev['match'])
                
                # Format & Encode Stream
                raw_link = ev.get('url', '')
                stream_obj = {
                    "source": "topembed", 
                    "id": obfuscate_link(str(raw_link)), # ENCODING APPLIED HERE
                    "resolution": "HD" 
                }

                matches.append({
                    "id": f"te_{ev['unix_timestamp']}_{ev['match'][:5].replace(' ','')}",
                    "title": ev['match'],
                    "sport": league,
                    "start_time": start_ms,
                    "viewers": 0, # TopEmbed doesn't provide viewers
                    "streams": [stream_obj],
                    "teams": {},
                    "image": "assets/fallback.jpg",
                    "origin": "topembed"
                })
        return matches
    except Exception as e:
        print(f"Error fetching TopEmbed: {e}")
        return []

# ==========================================
# MERGING LOGIC
# ==========================================

def merge_matches(master_list, backup_list):
    final_list = master_list.copy()
    
    for backup in backup_list:
        found = False
        for master in final_list:
            # Match Logic: Same Sport + Time within 45m
            time_diff = abs(master['start_time'] - backup['start_time'])
            
            if master['sport'] == backup['sport'] and time_diff < (45 * 60 * 1000):
                # Fuzzy Title Logic
                m_words = set(w.lower() for w in master['title'].split() if len(w) > 3)
                b_words = set(w.lower() for w in backup['title'].split() if len(w) > 3)
                
                # If titles share significant words, merge streams
                if m_words & b_words: 
                    master['streams'].extend(backup['streams'])
                    found = True
                    break
        
        # Add unique backup matches only if they are target sports
        if not found and backup['sport'] in USA_TARGETS:
            final_list.append(backup)
            
    return final_list

# ==========================================
# PROCESSING & RANKING
# ==========================================

def process_data(matches, config):
    output = {
        "updated": NOW_MS,
        "important": [],
        "categories": {},
        "home_schema": []
    }
    
    # Pre-calculate domain for schema
    domain = config['site_settings'].get('domain', 'localhost')

    for m in matches:
        # 1. Cleanup Old Matches (Keep if high viewers or barely finished)
        if NOW_MS > (m['start_time'] + (4 * 3600000)) and m['viewers'] < 50:
            continue
            
        # 2. Categorize
        if m['sport'] not in output['categories']:
            output['categories'][m['sport']] = []
        output['categories'][m['sport']].append(m)
        
        # 3. Hero Table Logic (Important)
        # Condition: Live OR (Target Sport & Starts < 1hr)
        time_diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS
        starts_soon = 0 < time_diff < 3600000 # 1 Hour

        m['is_live'] = is_live
        
        is_important = False
        if is_live and m['viewers'] > 50: is_important = True
        if starts_soon and m['sport'] in USA_TARGETS: is_important = True
        
        # Flag for frontend button
        # Show button if Live OR starts in < 30 mins
        m['show_button'] = is_live or (0 < time_diff < 1800000)

        if is_important:
            output['important'].append(m)
            
            # Schema for Important events
            output['home_schema'].append({
                "@context": "https://schema.org",
                "@type": "BroadcastEvent",
                "name": m['title'],
                "startDate": datetime.fromtimestamp(m['start_time']/1000).isoformat(),
                "eventStatus": "https://schema.org/EventLive" if is_live else "https://schema.org/EventScheduled",
                "location": {"@type": "Place", "name": "Online"},
                "url": f"https://{domain}/?watch={m['id']}"
            })

    # Sort by Viewers (Descending)
    output['important'].sort(key=lambda x: x['viewers'], reverse=True)
    
    return output

# ==========================================
# PAGE GENERATION (SSG)
# ==========================================

def generate_pages(data, config):
    # Load Template
    try:
        with open('assets/page_template.html', 'r') as f: template = f.read()
    except FileNotFoundError:
        print("Template not found. Skipping page gen.")
        return

    # Create Pages for Site Links
    for page_conf in config.get('site_links', []):
        slug = page_conf['slug'].strip('/')
        title = page_conf['title']
        
        # 1. Prepare Folder: /nfl/
        if not os.path.exists(slug):
            os.makedirs(slug, exist_ok=True)
            
        # 2. Prepare Data
        # We inject the specific category into the JS variable in the template
        article_path = f"data/articles/{slug}.html"
        article_content = ""
        if os.path.exists(article_path):
            with open(article_path, 'r') as af: article_content = af.read()

        # 3. Replace Placeholders
        html = template
        html = html.replace('{{TITLE}}', page_conf.get('meta_title', title))
        html = html.replace('{{DESC}}', page_conf.get('meta_desc', ''))
        html = html.replace('{{H1}}', title)
        html = html.replace('{{CATEGORY}}', title) # JS uses this to filter
        html = html.replace('{{ARTICLE}}', article_content)

        # 4. Save
        with open(f"{slug}/index.html", 'w') as f:
            f.write(html)
        print(f"Generated: {slug}/index.html")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("--- Starting Update ---")
    conf = load_config()
    
    # Fetch & Merge
    s_data = fetch_streamed_pk(conf['api_keys']['streamed_url'])
    t_data = fetch_topembed(conf['api_keys']['topembed_url'])
    merged = merge_matches(s_data, t_data)
    
    # Process (Encryption happens inside fetch functions)
    final_json = process_data(merged, conf)
    
    # Save Data
    with open('data/matches.json', 'w') as f:
        json.dump(final_json, f)
    print("matches.json saved.")
        
    # Build Pages
    generate_pages(final_json, conf)
    print("--- Update Complete ---")
