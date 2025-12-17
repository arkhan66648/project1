import json
import time
import requests
import os
import shutil
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================

# 1. League Detection (The "Classifier")
# Since Streamed.pk is generic, we check the Title & Category for these keywords.
# If "American Football" -> We assume NFL unless specific keywords say otherwise.
LEAGUE_KEYWORDS = {
    "NFL": ["NFL", "Super Bowl", "American Football"],
    "NBA": ["NBA", "Basketball", "Playoffs"],
    "NHL": ["NHL", "Ice Hockey", "Stanley Cup"],
    "MLB": ["MLB", "Baseball"],
    "UFC": ["UFC", "MMA", "Fighting", "Fight Night"],
    "F1": ["Formula 1", "F1", "Grand Prix"],
    "Boxing": ["Boxing", "Fight"],
    "Soccer": ["Soccer", "Premier League", "Champions League", "La Liga", "MLS"]
}

# 2. Priority Settings
USA_TARGETS = ["NFL", "NBA", "UFC", "NHL", "MLB"]
NOW_MS = int(time.time() * 1000)

def load_config():
    with open('data/config.json', 'r') as f:
        return json.load(f)

# ==========================================
# HELPER: CLASSIFY SPORT
# ==========================================
def detect_league(category, title):
    # Combine text for search
    text = (category + " " + title).upper()
    
    # Check specific leagues first
    for league, keywords in LEAGUE_KEYWORDS.items():
        for k in keywords:
            if k.upper() in text:
                # Grey Hat Logic: If it says "American Football", map to "NFL"
                # This aggregates all football under the high-traffic NFL keyword
                if category == "American Football": return "NFL" 
                if category == "Basketball": return "NBA"
                if category == "Fighting" or category == "MMA": return "UFC"
                return league
                
    return category # Fallback to original if no match

# ==========================================
# FETCHING DATA
# ==========================================

def fetch_streamed_pk(url):
    try:
        data = requests.get(url).json()
        matches = []
        for m in data:
            raw_cat = m.get('category', '')
            title = m.get('title', '')
            
            # Detect actual league (e.g., "Basketball" -> "NBA")
            league = detect_league(raw_cat, title)
            
            # Create standardized object
            matches.append({
                "id": str(m['id']),
                "title": title,
                "sport": league, # This will now say "NBA" instead of "Basketball"
                "start_time": m['date'], # ms
                "viewers": m.get('viewers', 0),
                "streams": m.get('sources', []), # Keep original structure
                "teams": m.get('teams', {}),
                "image": f"https://streamed.pk/api/images/poster/{m['teams']['home']['badge']}/{m['teams']['away']['badge']}.webp",
                "origin": "streamed"
            })
        return matches
    except Exception as e:
        print(f"Error Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    try:
        data = requests.get(url).json()
        matches = []
        for date_key, events in data.get('events', {}).items():
            for ev in events:
                # Convert Seconds to MS
                start_ms = ev['unix_timestamp'] * 1000
                
                # TopEmbed usually provides good league names, but we normalize
                raw_sport = ev.get('sport', '')
                league = detect_league(raw_sport, ev['match'])

                # Format Stream Link to match Streamed.pk structure
                # We label it "TopEmbed" so frontend knows how to handle it
                stream_obj = {
                    "source": "topembed", 
                    "id": ev.get('url', ''), 
                    "resolution": "HD" 
                }

                matches.append({
                    "id": f"te_{ev['unix_timestamp']}_{ev['match'][:5]}",
                    "title": ev['match'],
                    "sport": league,
                    "start_time": start_ms,
                    "viewers": 0,
                    "streams": [stream_obj],
                    "teams": {},
                    "image": "/assets/fallback.jpg", # Placeholder
                    "origin": "topembed"
                })
        return matches
    except Exception as e:
        print(f"Error TopEmbed: {e}")
        return []

# ==========================================
# MERGING LOGIC (COMBINING STREAMS)
# ==========================================

def merge_matches(master_list, backup_list):
    # We use master_list (Streamed) as the base because it has Images/Viewers
    final_list = master_list.copy()
    
    for backup in backup_list:
        found = False
        for master in final_list:
            # MATCHING LOGIC:
            # 1. Same Sport/League
            # 2. Start time within 45 mins
            time_diff = abs(master['start_time'] - backup['start_time'])
            
            if master['sport'] == backup['sport'] and time_diff < (45 * 60 * 1000):
                # CHECK TITLE SIMILARITY (Simple subset check)
                # If "Lakers" is in both titles, we assume match
                m_title = master['title'].lower()
                b_title = backup['title'].lower()
                
                # Very simple fuzzy match: do they share at least one long word (4+ chars)?
                m_words = set(w for w in m_title.split() if len(w) > 3)
                b_words = set(w for w in b_title.split() if len(w) > 3)
                
                if m_words & b_words: # Intersection exists
                    # MERGE STREAMS!
                    # We add the backup streams to the master streams list
                    # We flag them so frontend can style them differently if needed
                    print(f"Merging streams for: {master['title']}")
                    master['streams'].extend(backup['streams'])
                    found = True
                    break
        
        # If not found in Master, and it's a USA Target sport, add it
        if not found and backup['sport'] in USA_TARGETS:
            final_list.append(backup)
            
    return final_list

# ==========================================
# PROCESSING (PRIORITY & CLEANUP)
# ==========================================

def process_data(matches, config):
    output = {
        "updated": NOW_MS,
        "important": [], # Hero Table
        "categories": {}, # "NFL": [...], "NBA": [...]
        "schema": [] # Global Schema
    }
    
    for m in matches:
        # 1. Time Filters
        # Matches kept for 4 hours after start
        if NOW_MS > (m['start_time'] + (4 * 3600000)) and m['viewers'] < 100:
            continue
            
        # 2. Categorize
        if m['sport'] not in output['categories']:
            output['categories'][m['sport']] = []
        output['categories'][m['sport']].append(m)
        
        # 3. "Important" Logic (Hero Table)
        # Conditions: Live OR Starting in < 1hr (For USA Targets)
        starts_soon = 0 < (m['start_time'] - NOW_MS) < 3600000
        is_live = m['start_time'] <= NOW_MS
        
        is_hero = False
        if is_live and m['viewers'] > 50: is_hero = True
        if starts_soon and m['sport'] in USA_TARGETS: is_hero = True
        
        if is_hero:
            m['status_text'] = "LIVE NOW" if is_live else "STARTING SOON"
            output['important'].append(m)
            
            # Add Schema for Important Matches
            output['schema'].append({
                "@context": "https://schema.org",
                "@type": "BroadcastEvent",
                "name": m['title'],
                "startDate": datetime.fromtimestamp(m['start_time']/1000).isoformat(),
                "eventStatus": "https://schema.org/EventLive" if is_live else "https://schema.org/EventScheduled",
                "location": {"@type": "Place", "name": "Online"},
                "url": f"https://{config['site_settings']['domain']}/match?id={m['id']}"
            })

    # Sort Important by Priority (Viewers > Time)
    output['important'].sort(key=lambda x: x['viewers'], reverse=True)
    
    return output

# ==========================================
# FOLDER & PAGE GENERATION
# ==========================================

def generate_pages(data, config):
    # Load Template
    try:
        with open('assets/page_template.html', 'r') as f: template = f.read()
    except: return

    # Loop Configured Pages (e.g., NFL, NBA)
    for page_conf in config['site_links']:
        slug = page_conf['slug'].strip('/') # e.g. "nfl"
        
        # 1. Create Folder Structure: /nfl/
        folder_path = slug
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            
        # 2. Get Matches for this category
        cat_matches = data['categories'].get(page_conf['title'], [])
        
        # 3. Inject Data
        html = template
        html = html.replace('{{TITLE}}', page_conf['meta_title'])
        html = html.replace('{{DESC}}', page_conf['meta_desc'])
        html = html.replace('{{H1}}', page_conf['title'])
        html = html.replace('{{CATEGORY}}', page_conf['title']) # For JS Filter
        
        # Inject Article (if exists in data/articles/nfl.html)
        article_path = f"data/articles/{slug}.html"
        content = ""
        if os.path.exists(article_path):
            with open(article_path, 'r') as af: content = af.read()
        html = html.replace('{{ARTICLE}}', content)

        # 4. Save as index.html inside the folder
        with open(f"{folder_path}/index.html", 'w') as f:
            f.write(html)
        print(f"Generated: {folder_path}/index.html")

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    conf = load_config()
    
    # Fetch
    s_data = fetch_streamed_pk(conf['api_keys']['streamed_url'])
    t_data = fetch_topembed(conf['api_keys']['topembed_url'])
    
    # Merge (Streams combined here)
    merged = merge_matches(s_data, t_data)
    
    # Process
    final_json = process_data(merged, conf)
    
    # Save JSON
    with open('data/matches.json', 'w') as f:
        json.dump(final_json, f)
        
    # Build Site
    generate_pages(final_json, conf)
