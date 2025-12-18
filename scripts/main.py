import json
import time
import requests
import os
import base64
import sys
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & PRIORITY
# ==========================================
# Higher number = Appears higher in "Trending" and "Upcoming"
SPORT_PRIORITY = { 
    "NFL": 100, 
    "NBA": 90, 
    "UFC": 85, 
    "MLB": 80, 
    "NHL": 70, 
    "Soccer": 60, 
    "F1": 50,
    "Boxing": 45
}

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

USA_TARGETS = ["NFL", "NBA", "UFC", "NHL", "MLB"]
NOW_MS = int(time.time() * 1000)

def load_config():
    if not os.path.exists('data/config.json'):
        print("⚠️ Config not found. Using defaults.")
        return {}
    try:
        with open('data/config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading config: {e}")
        return {}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def obfuscate_link(link):
    if not link: return ""
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
# 3. DATA FETCHING
# ==========================================
def fetch_streamed_pk(url):
    if not url: return []
    print(f"Fetching Streamed.pk...")
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        for m in data:
            title = m.get('title', 'Unknown Match')
            raw_cat = m.get('category', 'Other')
            league = detect_league(raw_cat, title)
            
            processed_streams = []
            for src in m.get('sources', []):
                raw_link = src.get('url') or src.get('id') or ""
                processed_streams.append({
                    "source": src.get('source', 'streamed'),
                    "id": obfuscate_link(str(raw_link)),
                    "resolution": "HD"
                })

            matches.append({
                "id": str(m['id']),
                "title": title,
                "sport": league,
                "start_time": m['date'],
                "viewers": m.get('viewers', 0),
                "streams": processed_streams,
                "teams": m.get('teams', {}),
                "is_live": False 
            })
        return matches
    except Exception as e:
        print(f"❌ Error Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    if not url: return []
    print(f"Fetching TopEmbed...")
    try:
        data = requests.get(url, timeout=15).json()
        matches = []
        for date_key, events in data.get('events', {}).items():
            for ev in events:
                start_ms = int(ev['unix_timestamp']) * 1000
                league = detect_league(ev.get('sport', ''), ev['match'])
                raw_link = ev.get('url', '')
                
                matches.append({
                    "id": f"te_{ev['unix_timestamp']}_{ev['match'][:5].replace(' ','')}",
                    "title": ev['match'],
                    "sport": league,
                    "start_time": start_ms,
                    "viewers": 0,
                    "streams": [{"source": "topembed", "id": obfuscate_link(str(raw_link))}],
                    "teams": {},
                })
        return matches
    except Exception as e:
        print(f"❌ Error TopEmbed: {e}")
        return []

# ==========================================
# 4. MERGE & RANKING LOGIC
# ==========================================
def merge_matches(master_list, backup_list):
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
    output = { "updated": NOW_MS, "important": [], "categories": {} }
    
    for m in matches:
        # Cleanup Old matches (4 hours)
        if NOW_MS > (m['start_time'] + (14400000)) and m['viewers'] < 50: continue
            
        time_diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS
        m['is_live'] = is_live
        
        # Show Button logic
        m['show_button'] = is_live or (0 < time_diff < 1800000)

        # Assign USA Priority Score
        base_priority = SPORT_PRIORITY.get(m['sport'], 10)
        if is_live: base_priority += 200 # Live matches float to top
        m['priority'] = base_priority + (m['viewers'] / 100)

        # Categorize
        if m['sport'] not in output['categories']: output['categories'][m['sport']] = []
        output['categories'][m['sport']].append(m)
        
        # Hero Table Logic (Top Priority Only)
        is_hero = False
        if is_live and m['viewers'] > 50: is_hero = True
        if (0 < time_diff < 3600000) and m['sport'] in USA_TARGETS: is_hero = True
        
        if is_hero: output['important'].append(m)

    # Sort Trending by Calculated Priority
    output['important'].sort(key=lambda x: x['priority'], reverse=True)
    return output

# ==========================================
# 5. HTML GENERATOR (MASTER TEMPLATE)
# ==========================================
def build_single_page(template, config, page_data=None):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    soc = config.get('social_stats', {})
    
    # 1. Build HEADER Menu (Right Side)
    # Uses 'header_menu' from config
    header_menu_html = ""
    for item in config.get('header_menu', []):
        header_menu_html += f'<a href="{item["url"]}">{item["title"]}</a>'

    # 2. Build HERO PILLS (Categories)
    # Uses 'hero_categories' from config
    hero_pills_html = ""
    for item in config.get('hero_categories', []):
        path = f'/{item["folder"]}/index.html'
        # Check active state
        active_class = "active" if page_data and page_data['title'] == item['title'] else ""
        hero_pills_html += f'<a href="{path}" class="cat-pill {active_class}">{item["title"]}</a>'

    # 3. Build FOOTER Keywords
    footer_html = ""
    for kw in s.get('footer_keywords', []):
        if kw: footer_html += f'<a href="/?q={kw.strip()}" class="p-tag">{kw.strip()}</a>'

    # 4. INJECT VARIABLES
    html = template
    
    # Theme & Colors
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('status_green', '#00e676'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))

    # Site Identity
    html = html.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    html = html.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    html = html.replace('{{SITE_NAME}}', s.get('site_name', 'StreamEast'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', 'assets/logo.png'))
    html = html.replace('{{DOMAIN}}', s.get('domain', 'streameast.app'))
    html = html.replace('{{FAVICON}}', s.get('logo_url', 'assets/logo.png')) # Fallback to logo

    # Social Stats
    html = html.replace('{{SOC_TELEGRAM}}', soc.get('telegram', '12k'))
    html = html.replace('{{SOC_TWITTER}}', soc.get('twitter', '8k'))
    html = html.replace('{{SOC_DISCORD}}', soc.get('discord', '5k'))
    html = html.replace('{{SOC_REDDIT}}', soc.get('reddit', '3k'))

    # Content Injection
    html = html.replace('{{HEADER_MENU}}', header_menu_html)
    html = html.replace('{{HERO_PILLS}}', hero_pills_html)
    html = html.replace('{{FOOTER_KEYWORDS}}', footer_html)

    # Page Specifics
    if page_data:
        # SUBPAGE MODE
        html = html.replace('{{META_TITLE}}', page_data.get('meta_title', ''))
        html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
        html = html.replace('{{HOMEPAGE_ARTICLE}}', page_data.get('article', ''))
        
        # Fix paths for subfolder depth
        html = html.replace('href="assets', 'href="../assets')
        html = html.replace('src="assets', 'src="../assets')
        html = html.replace('href="/', 'href="../') 
        html = html.replace('data/matches.json', '../data/matches.json')

        # Inject JS Flag
        js_flag = f'window.PAGE_CATEGORY = "{page_data["title"]}"; window.IS_SUBPAGE = true;'
        if 'window.IS_SUBPAGE = false;' in html:
            html = html.replace('window.IS_SUBPAGE = false;', js_flag)
        else:
            html = html.replace('</body>', f'<script>{js_flag}</script></body>')
    else:
        # HOMEPAGE MODE
        html = html.replace('{{META_TITLE}}', s.get('meta_title', ''))
        html = html.replace('{{META_DESC}}', s.get('meta_desc', ''))
        
        # Load Homepage Article
        art = ""
        if os.path.exists('data/articles/home.html'):
            with open('data/articles/home.html', 'r', encoding='utf-8') as f: art = f.read()
        html = html.replace('{{HOMEPAGE_ARTICLE}}', art)

    # Static Schema
    static_schema = {
        "@context": "https://schema.org",
        "@graph": [
            { "@type": "WebSite", "name": s.get('site_name'), "url": f"https://{s.get('domain')}" },
            { "@type": "Organization", "name": s.get('site_name'), "logo": s.get('logo_url') }
        ]
    }
    html = html.replace('{{STATIC_SCHEMA}}', json.dumps(static_schema))

    return html

def generate_all_pages(config):
    print("Generating Pages...")
    
    # 1. LOAD TEMPLATE
    if not os.path.exists('assets/master_template.html'):
        print("❌ CRITICAL: assets/master_template.html NOT FOUND!")
        sys.exit(1)

    try:
        with open('assets/master_template.html', 'r', encoding='utf-8') as f: 
            template = f.read()
    except Exception as e:
        print(f"❌ Error reading template: {e}")
        sys.exit(1)

    # 2. GENERATE HOMEPAGE
    try:
        home_html = build_single_page(template, config, page_data=None)
        with open('index.html', 'w', encoding='utf-8') as f: f.write(home_html)
        print("✅ Saved index.html")
    except Exception as e:
        print(f"❌ Error saving index.html: {e}")

    # 3. GENERATE CATEGORY SUB-PAGES
    # Iterate over 'hero_categories' which serve as the main category pages
    for item in config.get('hero_categories', []):
        slug = item['folder'].strip('/')
        if not os.path.exists(slug): os.makedirs(slug, exist_ok=True)
        
        # Load Article
        cat_article = ""
        art_path = f"data/articles/{slug}.html"
        if os.path.exists(art_path):
            with open(art_path, 'r', encoding='utf-8') as f: cat_article = f.read()

        page_data = {
            'slug': slug,
            'title': item['title'], # This matches the Sport Name (e.g., "🏀 NBA")
            'meta_title': f"{item['title']} Live Streams - {config['site_settings'].get('site_name')}",
            'meta_desc': f"Watch {item['title']} live free.",
            'article': cat_article
        }

        sub_html = build_single_page(template, config, page_data)
        
        with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(sub_html)
        print(f"✅ Saved {slug}/index.html")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- Starting Update ---")
    
    os.makedirs('data', exist_ok=True)
    conf = load_config()
    
    # API
    s_data = fetch_streamed_pk(conf.get('api_keys', {}).get('streamed_url', ''))
    t_data = fetch_topembed(conf.get('api_keys', {}).get('topembed_url', ''))
    
    # Process
    merged = merge_matches(s_data, t_data)
    final_json = process_data(merged, conf)
    
    # Save Data
    with open('data/matches.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f)
    print("✅ matches.json saved.")
    
    # Build HTML
    generate_all_pages(conf)
    print("--- Update Complete ---")
