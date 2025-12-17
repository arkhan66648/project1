import json
import time
import requests
import os
import re
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION & STRATEGY
# ==========================================

# 1. Target USA Sports Only
# We filter strictly. If the API says "Cricket", we ignore it.
USA_PRIORITY_SPORTS = [
    "NFL", "NBA", "NHL", "MLB", "UFC", "MMA", "WWE", 
    "Boxing", "Formula 1", "NASCAR", "Soccer"
]

# 2. Sport Name Normalization
# APIs use different names. We map them to our standard.
SPORT_MAPPING = {
    "American Football": "NFL",
    "Basketball": "NBA",
    "Ice Hockey": "NHL",
    "Baseball": "MLB",
    "Fighting": "MMA"
}

# 3. Time Settings (Milliseconds)
NOW_MS = int(time.time() * 1000)
HOUR_MS = 3600000

# How long a match stays "Live" before being removed (if no viewers)
DURATION_MAP = {
    "NFL": 4 * HOUR_MS,
    "NBA": 3 * HOUR_MS,
    "MLB": 3.5 * HOUR_MS,
    "UFC": 5 * HOUR_MS,
    "Default": 2.5 * HOUR_MS
}

def load_config():
    with open('data/config.json', 'r') as f:
        return json.load(f)

# ==========================================
# FETCHING DATA
# ==========================================

def fetch_streamed_pk(url):
    try:
        data = requests.get(url).json()
        matches = []
        for m in data:
            # Map Category
            cat = m.get('category', 'Other')
            sport = SPORT_MAPPING.get(cat, cat)
            
            # Filter Non-USA (Optional: Keep everything but rank lower? 
            # User said: "sports like cricket... we won't keep")
            if sport not in USA_PRIORITY_SPORTS:
                continue

            matches.append({
                "id": m['id'],
                "title": m['title'],
                "sport": sport,
                "start_time": m['date'], # Already in MS
                "viewers": m.get('viewers', 0),
                "source": "streamed",
                "streams": m.get('sources', []),
                "teams": m.get('teams', {}),
                "is_master": True # This came from the rich API
            })
        return matches
    except Exception as e:
        print(f"Error fetching Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    try:
        data = requests.get(url).json()
        matches = []
        # Structure is events -> "date_string" -> list of matches
        for date_key, events in data.get('events', {}).items():
            for ev in events:
                # TopEmbed uses Seconds, convert to MS
                start_ms = ev['unix_timestamp'] * 1000
                
                # Check Keyword Filter
                raw_sport = ev.get('sport', '')
                tournament = ev.get('tournament', '')
                
                # Simple classification
                sport = "Other"
                found_sport = False
                for s in USA_PRIORITY_SPORTS:
                    if s.lower() in raw_sport.lower() or s.lower() in tournament.lower():
                        sport = s
                        found_sport = True
                        break
                
                if not found_sport: continue # Skip if not a target sport

                matches.append({
                    "id": f"te_{ev['unix_timestamp']}_{ev['match'][:5]}", # Fake ID
                    "title": ev['match'],
                    "sport": sport,
                    "start_time": start_ms,
                    "viewers": 0, # TopEmbed doesn't provide viewers
                    "source": "topembed",
                    "streams": [{"source": "topembed", "id": ev.get('url', '')}],
                    "is_master": False
                })
        return matches
    except Exception as e:
        print(f"Error fetching TopEmbed: {e}")
        return []

# ==========================================
# MERGING LOGIC (THE BRAIN)
# ==========================================

def merge_datasets(master_list, backup_list):
    final_list = master_list.copy()
    
    for backup in backup_list:
        # Check if this match already exists in master list
        # Logic: Same Sport AND Starts within 60 mins AND Similar Title
        match_found = False
        
        for master in final_list:
            time_diff = abs(master['start_time'] - backup['start_time'])
            
            # If same sport and close time (within 45 mins)
            if master['sport'] == backup['sport'] and time_diff < (45 * 60 * 1000):
                # Fuzzy Title Check (Simple version)
                # "Lakers vs Warriors" vs "Los Angeles Lakers - Golden State"
                # We assume if time + sport matches, it's likely the same event
                # We can add backup stream to master
                master['streams'].append({
                    "source": "topembed_backup",
                    "id": backup['id'] # or URL if available
                })
                match_found = True
                break
        
        # If not found in master, add it as a new match
        if not match_found:
            final_list.append(backup)
            
    return final_list

# ==========================================
# PROCESSING & RANKING
# ==========================================

def process_matches(matches, config):
    output_data = {
        "generated_at": NOW_MS,
        "important": [],
        "categories": {}, # Organized by sport
        "all_matches": [] 
    }
    
    all_schema = []

    for m in matches:
        # 1. Determine Status
        duration = DURATION_MAP.get(m['sport'], DURATION_MAP['Default'])
        end_time = m['start_time'] + duration
        
        is_live = m['start_time'] <= NOW_MS <= end_time
        is_upcoming = m['start_time'] > NOW_MS
        
        # If finished and no viewers, skip (Clean up)
        if NOW_MS > end_time and m['viewers'] < 50:
            continue

        # 2. Priority Score Calculation
        # Base Score
        score = 0
        if is_live: score += 1000
        score += m['viewers'] * 2 # Viewers are high value
        
        # Tier 1 Sports Boost
        if m['sport'] in ["NFL", "NBA", "UFC"]: score += 500
        if m['sport'] in ["Soccer", "MLB"]: score += 200
        
        # Upcoming Boost (if starting soon)
        time_until = m['start_time'] - NOW_MS
        if 0 < time_until < (30 * 60 * 1000): # Starts in 30 mins
            score += 300

        m['is_live'] = is_live
        m['score'] = score
        m['status_text'] = "LIVE" if is_live else "UPCOMING"
        
        # Button Logic (User Request: 30 mins before)
        m['show_button'] = is_live or (0 < time_until < (30 * 60 * 1000))

        # 3. Add to Categories
        if m['sport'] not in output_data['categories']:
            output_data['categories'][m['sport']] = []
        output_data['categories'][m['sport']].append(m)
        output_data['all_matches'].append(m)

        # 4. "Important" Section Logic
        # Must be Live OR Tier 1 starting in < 1 hour
        is_important = False
        if is_live and m['viewers'] > 100: is_important = True
        if m['sport'] in ["NFL", "NBA", "UFC"] and 0 < time_until < (60 * 60 * 1000): is_important = True
        
        if is_important:
            output_data['important'].append(m)

        # 5. Schema Generation
        schema = {
            "@context": "https://schema.org",
            "@type": "BroadcastEvent",
            "name": m['title'],
            "startDate": datetime.fromtimestamp(m['start_time']/1000).isoformat(),
            "endDate": datetime.fromtimestamp(end_time/1000).isoformat(),
            "eventStatus": "https://schema.org/EventLive" if is_live else "https://schema.org/EventScheduled",
            "location": {"@type": "Place", "name": "Online"},
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
                "url": f"https://{config['site_settings']['domain']}/match?id={m['id']}"
            }
        }
        m['schema'] = schema # Attach to match for frontend use
        if is_important: all_schema.append(schema)

    # Sort Lists by Score
    output_data['important'].sort(key=lambda x: x['score'], reverse=True)
    for sport in output_data['categories']:
        output_data['categories'][sport].sort(key=lambda x: x['score'], reverse=True)
    
    # Store global schema for the homepage
    output_data['home_schema'] = all_schema

    return output_data

# ==========================================
# PAGE GENERATION (HTML)
# ==========================================

def generate_static_pages(processed_data, config):
    # Read Template
    try:
        with open('assets/page_template.html', 'r') as f:
            template = f.read()
    except:
        print("Template not found, skipping page generation.")
        return

    # Create 'pages' directory if not exists
    if not os.path.exists('pages'):
        os.makedirs('pages')

    # Loop through Site Links from Config
    for page in config.get('site_links', []):
        slug = page['slug'].replace('/', '') # Clean slug
        title = page['title'] # e.g., NFL
        
        # Get Article Content (if exists)
        article_path = f"data/articles/{slug}.html"
        article_content = ""
        if os.path.exists(article_path):
            with open(article_path, 'r') as f:
                article_content = f.read()
        
        # Get Schema for this category (Upcoming matches)
        cat_matches = processed_data['categories'].get(title, [])
        cat_schema_json = json.dumps([m['schema'] for m in cat_matches[:5]]) # Limit to top 5

        # Replace Placeholders
        html = template.replace('{{META_TITLE}}', page.get('meta_title', title))
        html = template.replace('{{META_DESC}}', page.get('meta_desc', ''))
        html = template.replace('{{SITE_NAME}}', config['site_settings']['site_name'])
        html = template.replace('{{H1_TITLE}}', title + " Live Streams")
        html = template.replace('{{CATEGORY_SLUG}}', title) # Used by JS to filter
        html = template.replace('{{ARTICLE_CONTENT}}', article_content)
        html = template.replace('{{SCHEMA_JSON}}', cat_schema_json)

        # Write File
        with open(f"{slug}.html", 'w') as f:
            f.write(html)
        print(f"Generated page: {slug}.html")

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    print("Starting Match Update...")
    config = load_config()
    
    # 1. Fetch
    streamed_data = fetch_streamed_pk(config['api_keys']['streamed_url'])
    topembed_data = fetch_topembed(config['api_keys']['topembed_url'])
    
    print(f"Fetched: {len(streamed_data)} from Streamed, {len(topembed_data)} from TopEmbed")

    # 2. Merge
    merged_matches = merge_datasets(streamed_data, topembed_data)
    
    # 3. Process & Rank
    final_json = process_matches(merged_matches, config)
    
    # 4. Save JSON
    with open('data/matches.json', 'w') as f:
        json.dump(final_json, f, indent=2)
    print("Saved data/matches.json")

    # 5. Generate Pages
    generate_static_pages(final_json, config)

if __name__ == "__main__":
    main()
