import json
import time
import requests
import os
import base64
import sys
import hashlib
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
NOW_MS = int(time.time() * 1000)

# Priority Scores (Higher = Top of lists)
PRIORITY_USA = { 
    "NFL": 100, "NBA": 95, "UFC": 90, "MLB": 85, "NHL": 80, 
    "Soccer": 60, "F1": 50, "Boxing": 70, "Tennis": 40, "Golf": 30 
}

PRIORITY_UK = { 
    "Soccer": 100, "Boxing": 95, "F1": 90, "Tennis": 85, "Cricket": 80,
    "NFL": 70, "NBA": 60, "UFC": 75, "Rugby": 70, "Golf": 50
}

# Mapping Keywords to Categories
LEAGUE_KEYWORDS = {
    "NFL": ["NFL", "Super Bowl", "American Football"],
    "NBA": ["NBA", "Basketball", "Playoffs"],
    "NHL": ["NHL", "Ice Hockey", "Stanley Cup"],
    "MLB": ["MLB", "Baseball"],
    "UFC": ["UFC", "MMA", "Fighting", "Fight Night", "Bellator", "PFL"],
    "F1": ["Formula 1", "F1", "Grand Prix"],
    "Boxing": ["Boxing", "Fight", "Fury", "Canelo", "Joshua", "Usyk"],
    "Soccer": ["Soccer", "Premier League", "Champions League", "La Liga", "MLS", "Bundesliga", "Serie A", "Ligue 1", "EPL"],
    "Golf": ["Golf", "PGA", "Masters"],
    "Tennis": ["Tennis", "ATP", "WTA", "Open"]
}

TEAM_COLORS = ["#D00000", "#0056D2", "#008f39", "#7C3AED", "#FFD700", "#ff5722", "#00bcd4", "#e91e63"]

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

def get_stable_id(title, start_time_ms):
    # Robust ID: Hash of Title + StartTime (prevents expiration on JSON updates)
    raw = f"{title.lower().strip()}_{start_time_ms}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def detect_sport_and_league(category, title):
    text = (str(category) + " " + str(title)).upper()
    sport = "Other"
    for sp, keywords in LEAGUE_KEYWORDS.items():
        for k in keywords:
            if k.upper() in text:
                sport = sp
                break
        if sport != "Other": break
    
    league = category if category and category != sport else sport
    # Normalization
    if category == "American Football": league = "NFL"
    if category == "Basketball": league = "NBA"
    return sport, league

def generate_team_ui(title):
    teams = []
    parts = title.split(' vs ')
    if len(parts) < 2: parts = title.split(' - ')
    if len(parts) < 2: parts = [title]

    for name in parts:
        clean_name = name.strip()
        if not clean_name: continue
        letter = clean_name[0].upper()
        # Consistent color hashing
        hash_val = int(hashlib.md5(clean_name.encode('utf-8')).hexdigest(), 16)
        color = TEAM_COLORS[hash_val % len(TEAM_COLORS)]
        teams.append({"name": clean_name, "letter": letter, "color": color})
    return teams

def get_running_time(start_ms):
    # Backend calculation for "34'" or "HT"
    diff_mins = (NOW_MS - start_ms) // 60000
    if diff_mins < 0: return "" # Not started
    if diff_mins > 150: return "FT"
    return f"{diff_mins}'"

def format_time_12h(ts_ms, timezone_str):
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000, pytz.timezone(timezone_str))
        # Example: "7:30 PM ET"
        tz_abbr = dt.strftime('%Z')
        # Simplify common zones
        if timezone_str == 'US/Eastern': tz_abbr = 'ET'
        if timezone_str == 'US/Pacific': tz_abbr = 'PT'
        if timezone_str == 'Europe/London': tz_abbr = 'UK'
        
        return dt.strftime(f'%I:%M %p {tz_abbr}').lstrip('0')
    except:
        return ""

def format_date_compact(ts_ms, timezone_str):
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000, pytz.timezone(timezone_str))
        return dt.strftime('%b %d')
    except:
        return ""

# ==========================================
# 3. DATA FETCHING & PROCESSING
# ==========================================
def fetch_data_redundant(config):
    matches = []
    
    # Source 1: Streamed.pk
    url1 = config.get('api_keys', {}).get('streamed_url')
    if url1:
        try:
            print("Fetching Streamed.pk...")
            data = requests.get(url1, timeout=10).json()
            for m in data:
                title = m.get('title', 'Unknown')
                sport, league = detect_sport_and_league(m.get('category', ''), title)
                start = m.get('date', 0)
                
                processed_streams = []
                for src in m.get('sources', []):
                    link = src.get('url') or src.get('id') or ""
                    processed_streams.append({"id": obfuscate_link(str(link)), "source": "s1"})

                matches.append({
                    "id": get_stable_id(title, start),
                    "title": title,
                    "sport": sport,
                    "league": league,
                    "start_time": start,
                    "viewers": m.get('viewers', 0),
                    "streams": processed_streams
                })
        except Exception as e:
            print(f"⚠️ Primary API Failed: {e}")

    # Source 2: TopEmbed
    url2 = config.get('api_keys', {}).get('topembed_url')
    if url2:
        try:
            print("Fetching TopEmbed...")
            data = requests.get(url2, timeout=10).json()
            for date_key, events in data.get('events', {}).items():
                for ev in events:
                    start = int(ev['unix_timestamp']) * 1000
                    sport, league = detect_sport_and_league(ev.get('sport', ''), ev['match'])
                    link = ev.get('url', '')
                    matches.append({
                        "id": get_stable_id(ev['match'], start),
                        "title": ev['match'],
                        "sport": sport,
                        "league": league,
                        "start_time": start,
                        "viewers": 0,
                        "streams": [{"id": obfuscate_link(str(link)), "source": "s2"}]
                    })
        except Exception as e:
             print(f"⚠️ Backup API Failed: {e}")
             
    return matches

def merge_and_persist(new_matches):
    # LIVE SAFETY: Load previous JSON to save live matches if API drops them temporarily
    final_map = {}
    
    # 1. Load Old
    if os.path.exists('data/matches.json'):
        try:
            with open('data/matches.json', 'r') as f:
                old_data = json.load(f)
                for m in old_data.get('all_matches', []):
                    # Keep if live/active and not super old (>4h)
                    if m.get('is_live') or (NOW_MS - m['start_time'] < 14400000):
                        final_map[m['id']] = m
        except: pass

    # 2. Merge New (Overwrite old if exists, add new)
    for m in new_matches:
        if m['id'] in final_map:
            # Merge streams
            existing = final_map[m['id']]
            existing['streams'] = m['streams'] # Update links
            if m['viewers'] > 0: existing['viewers'] = m['viewers'] # Update viewers
        else:
            final_map[m['id']] = m

    return list(final_map.values())

def process_matches(matches, config):
    tgt = config.get('targeting', {})
    country = tgt.get('country', 'USA')
    tz_str = tgt.get('timezone', 'US/Eastern')
    
    wc_conf = config.get('wildcard', {})
    wc_cat = wc_conf.get('category', '')
    
    priority_map = PRIORITY_UK if country == 'UK' else PRIORITY_USA
    
    output = { 
        "updated": NOW_MS, 
        "config": {
            "wildcard": wc_conf,
            "targeting": tgt
        },
        "trending": [], 
        "wildcard_matches": [], 
        "categories": {}, 
        "all_matches": [] # Flat list for JS search
    }

    # Helper for sorting
    def get_score(m):
        base = priority_map.get(m['sport'], 10)
        return (base * 1000) + m.get('hype_viewers', 0)

    for m in matches:
        # Time Diff
        diff = m['start_time'] - NOW_MS
        is_live = m['start_time'] <= NOW_MS and diff > -10800000 # Live if started & < 3h old
        
        # Hype Engine
        raw_v = m['viewers']
        hype = raw_v * 15 if raw_v < 100 else (raw_v * 5 if raw_v > 50000 else raw_v * 10)
        
        m['is_live'] = is_live
        m['hype_viewers'] = int(hype)
        m['running_time'] = get_running_time(m['start_time']) if is_live else ""
        m['fmt_time'] = format_time_12h(m['start_time'], tz_str)
        m['fmt_date'] = format_date_compact(m['start_time'], tz_str)
        m['teams_ui'] = generate_team_ui(m['title'])
        m['show_button'] = is_live or (diff < 1800000) # Show button 30m before
        
        # Trending Logic (Top Priority)
        if is_live or (0 < diff < 3600000 and m['sport'] in ["NFL", "NBA", "UFC", "Soccer"]):
            output['trending'].append(m)

        # Wildcard Logic (Full Schedule)
        is_wildcard = wc_cat and (wc_cat.lower() in [m['sport'].lower(), m['league'].lower()])
        if is_wildcard and diff > -7200000: # Include recently finished too
            output['wildcard_matches'].append(m)
        
        # Category Logic (Standard)
        if not is_wildcard:
            sport = m['sport']
            if sport not in output['categories']: output['categories'][sport] = []
            output['categories'][sport].append(m)

        output['all_matches'].append(m)

    # Sorting
    output['trending'].sort(key=get_score, reverse=True)
    output['wildcard_matches'].sort(key=lambda x: x['start_time'])
    
    for s in output['categories']:
        output['categories'][s].sort(key=lambda x: x['start_time'])

    return output

# ==========================================
# 4. HTML GENERATOR (SSG)
# ==========================================
def generate_menu_html(items, type, config_pages):
    html = ""
    for item in items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        hl = 'style="color:var(--brand-primary)"' if item.get('highlight') else ''
        
        # Logic for types
        if type == 'hero':
            # Hero Pills
            active = "" # Logic handled in build_html per page
            html += f'<a href="{url}" class="cat-pill {active}" {hl}>{title}</a>'
        elif type == 'footer':
            # Footer Links
            html += f'<a href="{url}" class="p-tag" {hl}>{title}</a>'
        else:
            # Header
            html += f'<a href="{url}" {hl}>{title}</a>'
    return html

def build_html(template, config, matches_json, page_conf):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    tgt = config.get('targeting', {})
    
    # 1. Menus
    header_html = generate_menu_html(config.get('header_menu', []), 'header', config.get('pages'))
    hero_html = generate_menu_html(config.get('hero_categories', []), 'hero', config.get('pages'))
    footer_l_html = generate_menu_html(config.get('footer_league_menu', []), 'footer', config.get('pages'))
    footer_s_html = generate_menu_html(config.get('footer_static_menu', []), 'footer', config.get('pages'))

    # 2. Replacements
    html = template
    
    # Lang & SEO
    lang = "en-US" if tgt.get('country') == "USA" else "en-GB"
    html = html.replace('lang="en"', f'lang="{lang}"')
    
    # Theme Variables
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('status_green', '#00e676'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    
    # New Gradient & Footer Colors
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{TREND_GRADIENT}}', t.get('trend_gradient_start', '#140000'))
    html = html.replace('{{FOOTER_BG}}', t.get('footer_bg', '#000000'))
    
    # Site Identity
    html = html.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    html = html.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    html = html.replace('{{TITLE_C1}}', t.get('title_color_1', '#ffffff'))
    html = html.replace('{{TITLE_C2}}', t.get('title_color_2', '#D00000'))
    html = html.replace('{{SITE_NAME}}', s.get('domain', 'StreamEast')) # Domain as name fallback
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))

    # Page Specific
    html = html.replace('{{H1}}', page_conf.get('h1', 'Live Sports'))
    html = html.replace('{{HERO_TEXT}}', page_conf.get('hero_text', ''))
    html = html.replace('{{META_TITLE}}', page_conf.get('meta_title', ''))
    html = html.replace('{{META_DESC}}', page_conf.get('meta_desc', ''))
    html = html.replace('{{ARTICLE_CONTENT}}', page_conf.get('content', ''))

    # Layout Logic (Home vs Category vs Static)
    p_type = page_conf.get('type', 'static')
    is_home = page_conf.get('slug') == 'home'
    
    # Menus Injection
    html = html.replace('{{HEADER_MENU}}', header_html)
    
    if p_type == 'static':
        html = html.replace('{{HERO_PILLS}}', '') # No Hero pills on static
        html = html.replace('{{DISPLAY_SEARCH}}', 'none')
        html = html.replace('{{DISPLAY_MATCHES}}', 'none')
        html = html.replace('{{FOOTER_LEAGUE_MENU}}', '') # No league links
    else:
        # Schedule or Home
        html = html.replace('{{HERO_PILLS}}', hero_html)
        html = html.replace('{{DISPLAY_SEARCH}}', 'block' if is_home else 'none')
        html = html.replace('{{DISPLAY_MATCHES}}', 'block')
        html = html.replace('{{FOOTER_LEAGUE_MENU}}', footer_l_html)

    html = html.replace('{{FOOTER_STATIC_MENU}}', footer_s_html)

    # Analytics & Socials
    html = html.replace('{{GA_CODE}}', f"<script>window.GA_ID='{s.get('ga_id')}';</script>" if s.get('ga_id') else "")
    html = html.replace('{{CUSTOM_META}}', s.get('custom_meta', ''))
    html = html.replace('{{SOC_TELEGRAM}}', config.get('social_stats', {}).get('telegram', ''))
    html = html.replace('{{SOC_TWITTER}}', config.get('social_stats', {}).get('twitter', ''))
    html = html.replace('{{SOC_DISCORD}}', config.get('social_stats', {}).get('discord', ''))
    html = html.replace('{{SOC_REDDIT}}', config.get('social_stats', {}).get('reddit', ''))

    # JSON Config Injection for JS
    # This passes the Wildcard ID and Fallback text to Frontend
    js_config = {
        "pageType": p_type,
        "isHome": is_home,
        "category": page_conf.get('assigned_category', ''),
        "wildcard": config.get('wildcard', {}),
        "siteName": s.get('domain')
    }
    html = html.replace('//JS_CONFIG_HERE', f"window.SITE_CONFIG = {json.dumps(js_config)};")
    
    # Static Schema
    schema = []
    # 1. WebSite
    schema.append({
        "@context": "https://schema.org", "@type": "WebSite",
        "name": s.get('domain'), "url": f"https://{s.get('domain')}"
    })
    # 2. Org (If enabled)
    sch = page_conf.get('schemas', {})
    if sch.get('organization'):
        org = sch['organization']
        schema.append({
            "@context": "https://schema.org", "@type": "Organization",
            "name": org.get('name'), "url": f"https://{s.get('domain')}",
            "logo": org.get('logo'), "sameAs": org.get('socials', '').split(',')
        })
    # 3. FAQ
    if sch.get('faq'):
        faq_items = []
        for item in sch['faq'].get('items', []):
            faq_items.append({
                "@type": "Question", "name": item['q'],
                "acceptedAnswer": { "@type": "Answer", "text": item['a'] }
            })
        if faq_items:
            schema.append({
                "@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": faq_items
            })

    html = html.replace('{{STATIC_SCHEMA}}', json.dumps(schema))

    # Path fix for sub-pages
    if not is_home:
        html = html.replace('href="assets', 'href="../assets')
        html = html.replace('src="assets', 'src="../assets')
        html = html.replace('href="/', 'href="../') 
        html = html.replace('data/matches.json', '../data/matches.json')
        # Fix root link
        html = html.replace('href="../"', 'href="../"') 
    
    return html

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- 🚀 Starting StreamCMS Build ---")
    os.makedirs('data', exist_ok=True)
    
    conf = load_config()
    
    # 1. Fetch & Process
    raw_matches = fetch_data_redundant(conf)
    all_matches = merge_and_persist(raw_matches)
    final_json = process_matches(all_matches, conf)
    
    # 2. Save JSON
    with open('data/matches.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f)
    print("✅ data/matches.json updated")

    # 3. Build Pages
    if not os.path.exists('assets/master_template.html'):
        print("❌ Error: assets/master_template.html not found.")
        sys.exit(1)
        
    with open('assets/master_template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    pages = conf.get('pages', [])
    if not pages:
        # Default home if empty
        pages = [{"slug": "home", "type": "schedule", "h1": "Live Sports"}]

    for p in pages:
        html = build_html(template, conf, final_json, p)
        
        if p.get('slug') == 'home':
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            print("✅ Built Homepage (index.html)")
        else:
            # Folder-based pages
            slug = p['slug'].strip('/')
            os.makedirs(slug, exist_ok=True)
            with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(html)
            print(f"✅ Built Page: {slug}/index.html")

    print("--- ✨ Build Complete ---")
