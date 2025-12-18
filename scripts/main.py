import json
import time
import requests
import os
import base64
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
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
    # Load config or return default if missing to prevent crash
    if not os.path.exists('data/config.json'):
        print("Config not found, using defaults.")
        return {"site_settings": {}, "api_keys": {}, "theme": {}, "site_links": []}
    
    with open('data/config.json', 'r') as f:
        return json.load(f)

# ==========================================
# HELPER FUNCTIONS
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
# FETCHING DATA
# ==========================================
def fetch_streamed_pk(url):
    if not url: return []
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
                "is_live": False # Will calculate later
            })
        return matches
    except Exception as e:
        print(f"Error Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    if not url: return []
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
        print(f"Error TopEmbed: {e}")
        return []

# ==========================================
# MERGE & PROCESS
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
            
        # Determine Status
        time_diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS
        m['is_live'] = is_live
        
        # Show Button logic (Live or starts in 30 mins)
        m['show_button'] = is_live or (0 < time_diff < 1800000)

        # Categorize
        if m['sport'] not in output['categories']: output['categories'][m['sport']] = []
        output['categories'][m['sport']].append(m)
        
        # Hero Table Logic
        is_hero = False
        if is_live and m['viewers'] > 50: is_hero = True
        if (0 < time_diff < 3600000) and m['sport'] in USA_TARGETS: is_hero = True
        
        if is_hero: output['important'].append(m)

    # Sort
    output['important'].sort(key=lambda x: x['viewers'], reverse=True)
    return output

# ==========================================
# HTML GENERATOR (THEME ENGINE)
# ==========================================
def generate_html(data, config):
    print("Generating HTML...")
    
    # 1. Load Master Template
    try:
        with open('assets/master_template.html', 'r') as f: template = f.read()
    except FileNotFoundError:
        print("CRITICAL: assets/master_template.html not found.")
        return

    # 2. Prepare Variables
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    links = config.get('site_links', [])

    # 3. Build Navigation HTML
    nav_html = ""
    for link in links:
        slug = link['slug'].strip('/')
        nav_html += f'<a href="/{slug}/">{link["title"]}</a>\n'

    # 4. Inject Settings (Colors from Admin)
    # Default fallbacks provided in case config is empty
    html = template.replace('{{BRAND_PRIMARY}}', t.get('color_accent', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000')) # Fallback
    html = html.replace('{{ACCENT}}', t.get('color_accent', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('color_live', '#00e676'))
    
    html = html.replace('{{SITE_NAME}}', s.get('site_name', 'StreamEast'))
    html = html.replace('{{META_TITLE}}', s.get('meta_title', 'StreamEast Live'))
    html = html.replace('{{META_DESC}}', s.get('meta_desc', 'Watch Sports Free'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', 'assets/logo.png'))
    html = html.replace('{{DOMAIN}}', s.get('domain', 'streameast.app'))
    html = html.replace('{{NAV_LINKS}}', nav_html)

    # 5. Inject Article
    article_content = ""
    if os.path.exists('data/articles/home.html'):
        with open('data/articles/home.html', 'r') as f: article_content = f.read()
    html = html.replace('{{HOMEPAGE_ARTICLE}}', article_content)

    # 6. Build Static Schema
    static_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": s.get('site_name'),
                "url": f"https://{s.get('domain')}"
            },
            {
                "@type": "Organization",
                "name": s.get('site_name'),
                "logo": s.get('logo_url')
            }
        ]
    }
    html = html.replace('{{STATIC_SCHEMA}}', json.dumps(static_schema))

    # 7. Write Index
    with open('index.html', 'w') as f: f.write(html)
    print("Saved index.html")

    # 8. Generate Sub-pages (Categories)
    for link in links:
        slug = link['slug'].strip('/')
        if not os.path.exists(slug): os.makedirs(slug, exist_ok=True)
        
        # Determine article for this page
        cat_article = ""
        if os.path.exists(f"data/articles/{slug}.html"):
            with open(f"data/articles/{slug}.html", 'r') as f: cat_article = f.read()

        # Use same template but tweak title/article
        page_html = html.replace(s.get('meta_title'), link.get('meta_title', ''))
        page_html = page_html.replace(article_content, cat_article)
        
        # Inject Category JS flag
        # We replace the JS config block
        js_config = f'window.PAGE_CATEGORY = "{link["title"]}"; window.IS_SUBPAGE = true;'
        page_html = page_html.replace('window.IS_SUBPAGE = false;', js_config)
        
        # Fix Relative Paths for subfolder
        page_html = page_html.replace('href="assets/', 'href="../assets/')
        page_html = page_html.replace('src="assets/', 'src="../assets/')
        page_html = page_html.replace('src="data/matches.json', 'src="../data/matches.json')
        page_html = page_html.replace('href="/', 'href="../') # Fix logo link

        with open(f"{slug}/index.html", 'w') as f: f.write(page_html)
        print(f"Saved {slug}/index.html")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("Starting Update...")
    conf = load_config()
    
    # API Fetch
    s_data = fetch_streamed_pk(conf['api_keys'].get('streamed_url', ''))
    t_data = fetch_topembed(conf['api_keys'].get('topembed_url', ''))
    
    # Merge & Save
    merged = merge_matches(s_data, t_data)
    final_json = process_data(merged, conf)
    
    with open('data/matches.json', 'w') as f:
        json.dump(final_json, f)
    
    # Build Site
    generate_html(final_json, conf)
    print("Done.")
