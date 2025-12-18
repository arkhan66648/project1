import json
import time
import requests
import os
import base64
import sys
import hashlib
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & PRIORITY
# ==========================================
# High priority = Appears first in "Other Upcoming"
SPORT_PRIORITY = { 
    "NFL": 100, "NBA": 95, "UFC": 90, "MLB": 85, "NHL": 80, 
    "Soccer": 75, "F1": 70, "Boxing": 65, "Tennis": 60, "Golf": 50 
}

LEAGUE_KEYWORDS = {
    "NFL": ["NFL", "Super Bowl", "American Football"],
    "NBA": ["NBA", "Basketball", "Playoffs"],
    "NHL": ["NHL", "Ice Hockey", "Stanley Cup"],
    "MLB": ["MLB", "Baseball"],
    "UFC": ["UFC", "MMA", "Fighting", "Fight Night", "Bellator", "PFL"],
    "F1": ["Formula 1", "F1", "Grand Prix"],
    "Boxing": ["Boxing", "Fight", "Fury", "Canelo", "Joshua"],
    "Soccer": ["Soccer", "Premier League", "Champions League", "La Liga", "MLS", "Bundesliga", "Serie A", "Ligue 1", "EPL"],
    "Golf": ["Golf", "PGA", "Masters"],
    "Tennis": ["Tennis", "ATP", "WTA", "Open"]
}

# Teams map for color generation (Simple Hash fallback)
TEAM_COLORS = [
    "#D00000", "#0056D2", "#008f39", "#7C3AED", "#FFD700", "#ff5722", "#00bcd4", "#e91e63"
]

USA_TARGETS = ["NFL", "NBA", "UFC", "NHL", "MLB"]
NOW_MS = int(time.time() * 1000)

def load_config():
    if not os.path.exists('data/config.json'): return {}
    try:
        with open('data/config.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def obfuscate_link(link):
    if not link: return ""
    return base64.b64encode(link.encode('utf-8')).decode('utf-8')

def detect_sport_and_league(category, title):
    # Returns (Sport, League)
    text = (str(category) + " " + str(title)).upper()
    
    # 1. Identify Sport
    sport = "Other"
    for sp, keywords in LEAGUE_KEYWORDS.items():
        for k in keywords:
            if k.upper() in text:
                sport = sp
                break
        if sport != "Other": break
    
    # 2. Identify League (Sub-category)
    # If category is specific (e.g. "Premier League"), use it. 
    # If generic (e.g. "Soccer"), try to find better in title or keep generic.
    league = category if category and category != sport else sport
    
    # Clean up generic API categories
    if category == "American Football": league = "NFL"
    if category == "Basketball": league = "NBA"
    
    return sport, league

def generate_team_ui(title):
    # Parses title "Lakers vs Warriors" -> Data for bubbles
    teams = []
    
    # Splitters
    parts = title.split(' vs ')
    if len(parts) < 2: parts = title.split(' - ')
    
    # If still 1 part, it's a single competitor event (F1, Golf)
    if len(parts) < 2:
        parts = [title]

    for name in parts:
        clean_name = name.strip()
        if not clean_name: continue
        
        # Letter: First char
        letter = clean_name[0].upper()
        
        # Color: Hash the name to pick a consistent color
        hash_val = int(hashlib.md5(clean_name.encode('utf-8')).hexdigest(), 16)
        color = TEAM_COLORS[hash_val % len(TEAM_COLORS)]
        
        teams.append({
            "name": clean_name,
            "letter": letter,
            "color": color
        })
        
    return teams

def apply_hype_engine(real_viewers, sport):
    # Hype Engine Logic
    v = int(real_viewers)
    if v == 0: return 0
    
    multiplier = 1
    if v < 100: multiplier = 15
    elif 100 <= v < 10000: multiplier = 15
    elif 10000 <= v < 50000: multiplier = 10
    elif v >= 50000: multiplier = 5
    
    hype_viewers = v * multiplier
    
    # Safety Check: Cap low priority sports
    # Golf (Priority 50) shouldn't beat NFL (Priority 100) easily
    max_cap = SPORT_PRIORITY.get(sport, 50) * 2000 # Example: Golf max 100k, NFL max 200k (soft limits)
    
    # We don't hard cap, but we dampen "Other" sports
    if sport == "Other" and hype_viewers > 20000:
        hype_viewers = 20000 + (hype_viewers - 20000) // 10
        
    return int(hype_viewers)

# ==========================================
# 3. DATA FETCHING
# ==========================================
def fetch_streamed_pk(url):
    if not url: return []
    print("Fetching Streamed.pk...")
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        for m in data:
            title = m.get('title', 'Unknown Match')
            raw_cat = m.get('category', 'Other')
            sport, league = detect_sport_and_league(raw_cat, title)
            
            processed_streams = []
            for src in m.get('sources', []):
                raw_link = src.get('url') or src.get('id') or ""
                processed_streams.append({
                    "source": src.get('source', 'streamed'),
                    "id": obfuscate_link(str(raw_link))
                })

            matches.append({
                "id": str(m['id']),
                "title": title,
                "sport": sport,
                "league": league, # Sub-category
                "start_time": m['date'],
                "viewers": m.get('viewers', 0),
                "streams": processed_streams,
                "origin": "streamed"
            })
        return matches
    except Exception as e:
        print(f"❌ Error Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    if not url: return []
    print("Fetching TopEmbed...")
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        for date_key, events in data.get('events', {}).items():
            for ev in events:
                start_ms = int(ev['unix_timestamp']) * 1000
                sport, league = detect_sport_and_league(ev.get('sport', ''), ev['match'])
                raw_link = ev.get('url', '')
                
                matches.append({
                    "id": f"te_{ev['unix_timestamp']}_{ev['match'][:5].replace(' ','')}",
                    "title": ev['match'],
                    "sport": sport,
                    "league": league,
                    "start_time": start_ms,
                    "viewers": 0,
                    "streams": [{"source": "topembed", "id": obfuscate_link(str(raw_link))}],
                    "origin": "topembed"
                })
        return matches
    except Exception as e:
        print(f"❌ Error TopEmbed: {e}")
        return []

# ==========================================
# 4. PROCESSING (The Brain)
# ==========================================
def merge_matches(master_list, backup_list):
    # Standard fuzzy merge
    final_list = master_list.copy()
    for backup in backup_list:
        found = False
        for master in final_list:
            time_diff = abs(master['start_time'] - backup['start_time'])
            if master['sport'] == backup['sport'] and time_diff < (45 * 60 * 1000):
                m_words = set(w.lower() for w in master['title'].split() if len(w) > 3)
                b_words = set(w.lower() for w in backup['title'].split() if len(w) > 3)
                if m_words & b_words: 
                    master['streams'].extend(backup['streams'])
                    found = True
                    break
        if not found and backup['sport'] in USA_TARGETS:
            final_list.append(backup)
    return final_list

def process_data(matches, config):
    output = { 
        "updated": NOW_MS, 
        "important": [], # Trending
        "categories": {}, # Upcoming by Sport
        "all_matches": [] # Flat list for search
    }
    
    # Track IDs that are trending to deduplicate from upcoming
    trending_ids = set()

    for m in matches:
        # 1. Cleanup Old Matches (4 hours)
        if NOW_MS > (m['start_time'] + 14400000) and m['viewers'] < 50: continue
        
        # 2. Time Logic
        time_diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS
        
        # 3. Hype Engine (Viewers)
        real_viewers = m['viewers']
        hype_viewers = apply_hype_engine(real_viewers, m['sport'])
        
        # 4. Enhance Object
        m['is_live'] = is_live
        m['viewers'] = hype_viewers # Overwrite with Hype number for Frontend
        m['show_button'] = is_live or (0 < time_diff < 1800000) # 30 mins
        m['teams_ui'] = generate_team_ui(m['title']) # CSS Circles
        
        # 5. Trending Logic (Top Priority)
        # Live matches OR Big US Sports starting in < 1 hr
        is_trending = False
        if is_live: is_trending = True
        elif (0 < time_diff < 3600000) and m['sport'] in ["NFL", "NBA", "UFC"]: is_trending = True
        
        if is_trending:
            output['important'].append(m)
            trending_ids.add(m['id'])
            
        # 6. Add to Global List (For Search)
        output['all_matches'].append(m)

    # 7. Categorize Upcoming (Deduplicated)
    # We loop again or filter the 'all_matches'
    # Requirements: Exclude trending from upcoming list
    for m in output['all_matches']:
        if m['id'] in trending_ids: continue # Skip if already in trending
        
        sport = m['sport']
        if sport not in output['categories']: output['categories'][sport] = []
        output['categories'][sport].append(m)

    # 8. Sort Trending (Priority + Viewers)
    # Give weight to Sport Priority so "Golf" with fake views doesn't beat "NFL"
    def sort_score(x):
        p = SPORT_PRIORITY.get(x['sport'], 10)
        return (p * 1000) + x['viewers']
        
    output['important'].sort(key=sort_score, reverse=True)
    
    # 9. Sort Upcoming Categories (Time asc)
    for sport in output['categories']:
        output['categories'][sport].sort(key=lambda x: x['start_time'])

    return output

# ==========================================
# 5. HTML GENERATOR (SSG)
# ==========================================
def build_html(template, config, page_conf):
    """
    page_conf: { slug, type, h1, hero_text, meta_title, meta_desc, content }
    """
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    soc = config.get('social_stats', {})
    
    # --- 1. PREPARE STATIC CONTENT ---
    
    # Header Menu (Right)
    header_menu = ""
    for item in config.get('header_menu', []):
        header_menu += f'<a href="{item["url"]}">{item["title"]}</a>'
        
    # Hero Pills (Categories)
    hero_pills = ""
    for item in config.get('hero_categories', []):
        # Active state logic
        # Use .get() to avoid crash, fallback to h1 if title is missing
page_title = page_conf.get('title', page_conf.get('h1', ''))
is_active = "active" if page_title == item['title'] else ""
        path = f"/{item['folder']}/"
        hero_pills += f'<a href="{path}" class="cat-pill {is_active}">{item["title"]}</a>'

    # Footer Keywords
    footer_kw = ""
    for k in s.get('footer_keywords', []):
        if k: footer_kw += f'<span class="p-tag" onclick="handlePartnerTerm(\'{k.strip()}\')">{k.strip()}</span>'

    # --- 2. LAYOUT LOGIC BASED ON TYPE ---
    
    # Show/Hide Sections based on Page Type
    search_style = 'block' if page_conf['type'] in ['home', 'schedule'] else 'none'
    matches_style = 'block' if page_conf['type'] in ['home', 'schedule'] else 'none'
    
    # If specific category page (e.g. NBA), JS needs to know
    js_category = page_conf['title'] if page_conf['type'] == 'schedule' and page_conf['slug'] != 'home' else 'home'
    
    # --- 3. INJECT VARIABLES ---
    html = template
    
    # Theme
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('status_green', '#00e676'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    html = html.replace('italic', 'italic' if t.get('title_italic') else 'normal') # Title Style

    # Identity
    html = html.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    html = html.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    html = html.replace('{{TITLE_C1}}', t.get('title_color_1', '#ffffff'))
    html = html.replace('{{TITLE_C2}}', t.get('title_color_2', '#D00000'))
    html = html.replace('{{SITE_NAME}}', s.get('site_name', 'StreamEast'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))

    # Socials
    html = html.replace('{{SOC_TELEGRAM}}', soc.get('telegram', '12k'))
    html = html.replace('{{SOC_TWITTER}}', soc.get('twitter', '8k'))
    html = html.replace('{{SOC_DISCORD}}', soc.get('discord', '5k'))
    html = html.replace('{{SOC_REDDIT}}', soc.get('reddit', '3k'))

    # Menus
    html = html.replace('{{HEADER_MENU}}', header_menu)
    html = html.replace('{{HERO_PILLS}}', hero_pills)
    html = html.replace('{{FOOTER_KEYWORDS}}', footer_kw)

    # Page Data
    html = html.replace('{{H1}}', page_conf['h1'])
    html = html.replace('{{HERO_TEXT}}', page_conf['hero_text'])
    html = html.replace('{{META_TITLE}}', page_conf['meta_title'])
    html = html.replace('{{META_DESC}}', page_conf['meta_desc'])
    html = html.replace('{{ARTICLE_CONTENT}}', page_conf['content'])
    
    # Layout Visibility
    html = html.replace('{{DISPLAY_SEARCH}}', search_style)
    html = html.replace('{{DISPLAY_MATCHES}}', matches_style)

    # Google Analytics & Meta
    ga_code = ""
    if s.get('ga_id'):
        ga_code = f"<script>window.GA_ID='{s['ga_id']}';</script>"
    html = html.replace('{{GA_CODE}}', ga_code)
    html = html.replace('{{CUSTOM_META}}', s.get('custom_meta', ''))

    # Paths & JS Config
    # If subpage (not root), fix relative paths
    if page_conf['slug'] != 'home':
        html = html.replace('href="assets', 'href="../assets')
        html = html.replace('src="assets', 'src="../assets')
        html = html.replace('href="/', 'href="../') 
        html = html.replace('data/matches.json', '../data/matches.json')
    
    js_config = f'window.PAGE_CATEGORY = "{js_category}"; window.IS_SUBPAGE = {str(page_conf["slug"] != "home").lower()};'
    html = html.replace('//JS_CONFIG_HERE', js_config)

    # Schema
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": s.get('site_name'),
        "url": f"https://{s.get('domain')}"
    }
    html = html.replace('{{STATIC_SCHEMA}}', json.dumps(schema))

    return html

def generate_site(config):
    print("Building Site...")
    
    if not os.path.exists('assets/master_template.html'):
        print("❌ Template not found")
        sys.exit(1)
    
    with open('assets/master_template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    # Iterate Pages defined in Admin
    pages = config.get('pages', [])
    # Fallback if no pages defined
    if not pages: 
        pages = [{"title": "Home", "slug": "home", "type": "schedule", "h1": "Live Sports", "hero_text": "Welcome", "meta_title": "Home", "content": ""}]

    for p in pages:
        # Prepare Data
        html = build_html(template, config, p)
        
        # Save File
        if p['slug'] == 'home':
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            print("✅ Built Homepage")
        else:
            # Create folder for slug (e.g. /nfl/)
            slug_dir = p['slug'].strip('/')
            if not os.path.exists(slug_dir): os.makedirs(slug_dir, exist_ok=True)
            with open(f"{slug_dir}/index.html", 'w', encoding='utf-8') as f: f.write(html)
            print(f"✅ Built {slug_dir}/index.html")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("--- Starting Build ---")
    os.makedirs('data', exist_ok=True)
    conf = load_config()
    
    # 1. Fetch & Process
    s_data = fetch_streamed_pk(conf.get('api_keys', {}).get('streamed_url', ''))
    t_data = fetch_topembed(conf.get('api_keys', {}).get('topembed_url', ''))
    merged = merge_matches(s_data, t_data)
    final_json = process_data(merged, conf)
    
    with open('data/matches.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f)
        
    # 2. Build Site (SSG)
    generate_site(conf)
    print("--- Complete ---")
