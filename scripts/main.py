import json
import time
import requests
import os
import base64
import sys

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
    if not os.path.exists('data/config.json'):
        print("⚠️ Config not found at data/config.json. Using defaults.")
        return {"site_settings": {}, "api_keys": {}, "theme": {}, "site_links": []}
    
    try:
        with open('data/config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading config: {e}")
        return {"site_settings": {}, "api_keys": {}, "theme": {}, "site_links": []}

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
    print(f"Fetching Streamed.pk from: {url}")
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
        print(f"✅ Streamed.pk: Found {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"❌ Error Streamed.pk: {e}")
        return []

def fetch_topembed(url):
    if not url: return []
    print(f"Fetching TopEmbed from: {url}")
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
        print(f"✅ TopEmbed: Found {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"❌ Error TopEmbed: {e}")
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
        if NOW_MS > (m['start_time'] + (14400000)) and m['viewers'] < 50: continue
            
        time_diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS
        m['is_live'] = is_live
        m['show_button'] = is_live or (0 < time_diff < 1800000)

        if m['sport'] not in output['categories']: output['categories'][m['sport']] = []
        output['categories'][m['sport']].append(m)
        
        is_hero = False
        if is_live and m['viewers'] > 50: is_hero = True
        if (0 < time_diff < 3600000) and m['sport'] in USA_TARGETS: is_hero = True
        
        if is_hero: output['important'].append(m)

    output['important'].sort(key=lambda x: x['viewers'], reverse=True)
    return output

# ==========================================
# HTML GENERATOR
# ==========================================
def build_single_page(template, config, page_data=None):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    links = config.get('site_links', [])

    # Navigation HTML
    nav_html = ""
    for link in links:
        slug = link['slug'].strip('/')
        nav_html += f'<a href="/{slug}/">{link["title"]}</a>\n'

    # Inject Variables
    html = template
    html = html.replace('{{BRAND_PRIMARY}}', t.get('color_accent', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT}}', t.get('color_accent', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('color_live', '#00e676'))
    
    html = html.replace('{{SITE_NAME}}', s.get('site_name', 'StreamEast'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', '/assets/streameast-logo-hd.jpg'))
    html = html.replace('{{DOMAIN}}', s.get('domain', 'streameast.app'))
    html = html.replace('{{NAV_LINKS}}', nav_html)

    if page_data:
        # SUBPAGE
        html = html.replace('{{META_TITLE}}', page_data.get('meta_title', ''))
        html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
        html = html.replace('{{HOMEPAGE_ARTICLE}}', page_data.get('article', ''))
        
        # Adjust Relative Paths
        html = html.replace('src="/assets', 'src="../assets')
        html = html.replace('href="/assets', 'href="../assets')
        html = html.replace('href="/', 'href="../') 
        html = html.replace('data/matches.json', '../data/matches.json')

        js_config = f'window.PAGE_CATEGORY = "{page_data["title"]}"; window.IS_SUBPAGE = true;'
        if 'window.IS_SUBPAGE = false;' in html:
            html = html.replace('window.IS_SUBPAGE = false;', js_config)
        else:
            html = html.replace('</body>', f'<script>{js_config}</script></body>')
    else:
        # HOMEPAGE
        html = html.replace('{{META_TITLE}}', s.get('meta_title', ''))
        html = html.replace('{{META_DESC}}', s.get('meta_desc', ''))
        
        article_content = ""
        if os.path.exists('data/articles/home.html'):
            with open('data/articles/home.html', 'r', encoding='utf-8') as f: article_content = f.read()
        html = html.replace('{{HOMEPAGE_ARTICLE}}', article_content)

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
    
    # 1. LOAD TEMPLATE (With Error Checking)
    if not os.path.exists('assets/master_template.html'):
        print("❌ CRITICAL ERROR: assets/master_template.html NOT FOUND!")
        print(f"Current Directory: {os.getcwd()}")
        print(f"Directory Contents: {os.listdir('.')}")
        if os.path.exists('assets'):
            print(f"Assets Contents: {os.listdir('assets')}")
        sys.exit(1) # Force workflow failure so you see red x

    try:
        # FORCE UTF-8 TO HANDLE EMOJIS 🏀
        with open('assets/master_template.html', 'r', encoding='utf-8') as f: 
            template = f.read()
    except Exception as e:
        print(f"❌ Error reading template: {e}")
        sys.exit(1)

    # 2. HOMEPAGE
    try:
        home_html = build_single_page(template, config, page_data=None)
        with open('index.html', 'w', encoding='utf-8') as f: f.write(home_html)
        print("✅ Saved index.html")
    except Exception as e:
        print(f"❌ Error saving index.html: {e}")
        sys.exit(1)

    # 3. SUBPAGES
    for link in config.get('site_links', []):
        slug = link['slug'].strip('/')
        if not os.path.exists(slug): os.makedirs(slug, exist_ok=True)
        
        cat_article = ""
        article_path = f"data/articles/{slug}.html"
        if os.path.exists(article_path):
            with open(article_path, 'r', encoding='utf-8') as f: cat_article = f.read()

        page_data = {
            'slug': slug,
            'title': link['title'],
            'meta_title': link.get('meta_title', link['title']),
            'meta_desc': link.get('meta_desc', ''),
            'article': cat_article
        }

        sub_html = build_single_page(template, config, page_data)
        
        with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(sub_html)
        print(f"✅ Saved {slug}/index.html")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- Starting Match Update ---")
    
    # Ensure data folder exists
    os.makedirs('data', exist_ok=True)
    
    conf = load_config()
    
    s_data = fetch_streamed_pk(conf['api_keys'].get('streamed_url', ''))
    t_data = fetch_topembed(conf['api_keys'].get('topembed_url', ''))
    
    merged = merge_matches(s_data, t_data)
    final_json = process_data(merged, conf)
    
    # Save with UTF-8
    with open('data/matches.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f)
    print("✅ matches.json saved.")
    
    generate_all_pages(conf)
    print("--- Update Complete ---")
