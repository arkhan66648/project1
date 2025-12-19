import json
import time
import requests
import os
import base64
import sys
import hashlib
import re
from datetime import datetime, timedelta

# Handle Timezones (Standard Library in Python 3.9+)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone as ZoneInfo

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
NOW_MS = int(time.time() * 1000)

# Priority Scores (Higher = Top of lists)
PRIORITY_USA = { 
    "NFL": 100, "NBA": 95, "UFC": 90, "MLB": 85, "NHL": 80, 
    "NCAA Football": 78, "NCAA Basketball": 75,
    "Soccer": 60, "F1": 50, "Boxing": 70, "Tennis": 40, "Golf": 30 
}

PRIORITY_UK = { 
    "Soccer": 100, "Boxing": 95, "F1": 90, "Tennis": 85, "Cricket": 80,
    "NFL": 70, "NBA": 60, "UFC": 75, "Rugby": 70, "Golf": 50
}

# Color palette for Team Icons
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

def clean_channel_name(raw_url):
    # Extracts readable name from TopEmbed links
    try:
        if '[' in raw_url:
            parts = raw_url.split('/channel/')
            if len(parts) > 1:
                name = parts[1].split('[')[0]
                return name.replace('-', ' ').upper()
    except: pass
    return "HD STREAM"

def get_robust_id(title, start_time_ms):
    # Generates ID from "Team A vs Team B" + "YYYY-MM-DD"
    # This ensures ID stays same even if time shifts slightly
    separator = ' vs ' if ' vs ' in title else ' - '
    teams = re.split(r'\s+vs\.?\s+|\s+-\s+', title.lower())
    
    # Sort teams so "A vs B" = "B vs A"
    teams.sort()
    clean_teams = "".join([t.strip() for t in teams if t.strip()])
    
    # Get Date String (Timezone neutral for ID)
    date_str = datetime.fromtimestamp(start_time_ms / 1000).strftime('%Y%m%d')
    
    raw = f"{clean_teams}_{date_str}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def detect_sport_normalized(raw_sport, raw_league):
    # CRITICAL: Fixes NCAA showing as NBA
    s = str(raw_sport).upper()
    l = str(raw_league).upper()
    title_combined = s + " " + l

    if "BASKETBALL" in s:
        if "COLLEGE" in l or "NCAA" in l: return "NCAA Basketball"
        if "NBA" in l: return "NBA"
        return "Basketball"
        
    if "FOOTBALL" in s or "AMERICAN FOOTBALL" in s:
        if "COLLEGE" in l or "NCAA" in l: return "NCAA Football"
        if "NFL" in l: return "NFL"
        return "American Football"

    if "HOCKEY" in s: return "NHL" if "NHL" in l else "Ice Hockey"
    if "BASEBALL" in s: return "MLB" if "MLB" in l else "Baseball"
    if "SOCCER" in s: return "Soccer"
    if "FIGHT" in s or "MMA" in s or "UFC" in s: return "UFC"
    if "BOXING" in s: return "Boxing"
    if "RACING" in s or "F1" in s: return "F1"
    if "TENNIS" in s: return "Tennis"
    if "CRICKET" in s: return "Cricket"
    if "GOLF" in s: return "Golf"
    
    return raw_sport.title() or "Other"

def generate_team_ui(title):
    teams = []
    # Split by common separators (vs, -, v)
    parts = re.split(r'\s+vs\.?\s+|\s+-\s+|\s+v\s+', title)
    
    # Limit to 2 teams
    for name in parts[:2]:
        clean = name.strip()
        if not clean: continue
        letter = clean[0].upper()
        # Hash name to pick a consistent color
        hash_val = int(hashlib.md5(clean.encode('utf-8')).hexdigest(), 16)
        color = TEAM_COLORS[hash_val % len(TEAM_COLORS)]
        teams.append({"name": clean, "letter": letter, "color": color})
    return teams

def get_running_time(start_ms):
    # Calculates minutes played for Live status
    diff_mins = (NOW_MS - start_ms) // 60000
    if diff_mins < 0: return "Starts Soon"
    if diff_mins > 180: return "FT"
    return f"{diff_mins}'"

def format_display_time(ts_ms, timezone_str):
    try:
        # Use Admin selected timezone
        tz = ZoneInfo(timezone_str)
        dt = datetime.fromtimestamp(ts_ms / 1000, tz)
        return dt.strftime('%I:%M %p').lstrip('0')
    except:
        return "--:--"

def format_display_date(ts_ms, timezone_str):
    try:
        tz = ZoneInfo(timezone_str)
        dt = datetime.fromtimestamp(ts_ms / 1000, tz)
        return dt.strftime('%b %d')
    except:
        return ""

# ==========================================
# 3. API FETCHING
# ==========================================
def fetch_topembed(url):
    matches = []
    if not url: return matches
    
    print(f"Fetching TopEmbed: {url}")
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200: return matches
        
        data = res.json()
        events_map = data.get('events', {})
        
        # Iterate through dates
        for date_key, event_list in events_map.items():
            for ev in event_list:
                try:
                    # TopEmbed uses Unix Timestamp (Seconds) -> Convert to MS
                    start_ms = int(ev['unixTimestamp']) * 1000
                except: continue

                title = ev.get('match', 'Unknown Match')
                raw_sport = ev.get('sport', 'Other')
                raw_tourn = ev.get('tournament', '') # This is the League!
                
                # Normalize Category (Fix NCAA/NBA)
                sport = detect_sport_normalized(raw_sport, raw_tourn)
                
                # Use tournament as league, fallback to sport
                league = raw_tourn if raw_tourn else sport

                # Extract Streams
                streams = []
                channels = ev.get('channels', [])
                # Handle inconsistent API formats (sometimes list of strings, sometimes objects)
                if isinstance(channels, list):
                    for ch in channels:
                        link = ""
                        if isinstance(ch, str): link = ch
                        elif isinstance(ch, dict): link = ch.get('channel', '')
                        
                        if link:
                            name = clean_channel_name(link)
                            streams.append({
                                "id": obfuscate_link(link), 
                                "name": name, 
                                "source": "te"
                            })

                matches.append({
                    "id": get_robust_id(title, start_ms),
                    "title": title,
                    "sport": sport,
                    "league": league, # Extracted from 'tournament'
                    "start_time": start_ms,
                    "viewers": 0, # TopEmbed provides no viewers
                    "streams": streams,
                    "origin": "topembed"
                })
    except Exception as e:
        print(f"❌ TopEmbed Error: {e}")
    
    return matches

def fetch_streamed(url):
    matches = []
    if not url: return matches
    
    print(f"Fetching Streamed: {url}")
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200: return matches
        data = res.json()
        
        for m in data:
            try: start_ms = int(m.get('date', 0))
            except: start_ms = NOW_MS + 3600000 

            title = m.get('title', 'Unknown')
            raw_cat = m.get('category', 'Other')
            sport = detect_sport_normalized(raw_cat, title)
            
            streams = []
            for src in m.get('sources', []):
                link = src.get('url') or src.get('id') or ""
                streams.append({
                    "id": obfuscate_link(link),
                    "name": src.get('source', 'Stream'),
                    "source": "spk"
                })

            matches.append({
                "id": get_robust_id(title, start_ms),
                "title": title,
                "sport": sport,
                "league": sport, # Streamed often lacks league, default to Sport
                "start_time": start_ms,
                "viewers": int(m.get('viewers', 0)),
                "streams": streams,
                "origin": "streamed"
            })
    except Exception as e:
        print(f"❌ Streamed Error: {e}")

    return matches

# ==========================================
# 4. PROCESSING & MERGING
# ==========================================
def merge_matches(list1, list2):
    # Master dictionary keyed by Robust ID
    master = {}
    
    # 1. Add List 1 (TopEmbed) - Prioritize for Titles/Leagues
    for m in list1:
        master[m['id']] = m
        
    # 2. Merge List 2 (Streamed) - Prioritize for Viewers/Links
    for m in list2:
        mid = m['id']
        if mid in master:
            existing = master[mid]
            # Add streams
            existing['streams'].extend(m['streams'])
            # Update Viewers (Streamed has real data)
            if m['viewers'] > existing['viewers']:
                existing['viewers'] = m['viewers']
            # Fallback League: If TopEmbed failed to give league, use Streamed
            if existing['league'] == 'Other' and m['league'] != 'Other':
                existing['league'] = m['league']
        else:
            master[mid] = m
            
    return list(master.values())

def load_previous_live_matches():
    # PERSISTENCE: Don't delete matches that were Live recently
    # This prevents streams from cutting off if API glitches
    kept_matches = []
    if os.path.exists('data/matches.json'):
        try:
            with open('data/matches.json', 'r') as f:
                old = json.load(f)
                for m in old.get('all_matches', []):
                    # Keep if it was live/trending and started less than 4 hours ago
                    if m.get('is_live', False) or (NOW_MS - m['start_time'] < 14400000):
                        kept_matches.append(m)
        except: pass
    return kept_matches

def process_data(matches, config):
    # 1. Load Config Settings
    tgt = config.get('targeting', {})
    country = tgt.get('country', 'USA')
    tz_str = tgt.get('timezone', 'US/Eastern')
    
    p_map = PRIORITY_UK if country == 'UK' else PRIORITY_USA
    
    wc_conf = config.get('wildcard', {})
    wc_cat = wc_conf.get('category', '').lower()
    
    # 2. Persistence Merge
    # We combine current API data with "Safety" data from previous run
    old_live = load_previous_live_matches()
    match_map = {m['id']: m for m in matches}
    
    for old in old_live:
        if old['id'] not in match_map:
            match_map[old['id']] = old # Restore lost live match
    
    final_list = list(match_map.values())

    output = {
        "trending": [],
        "wildcard_matches": [],
        "categories": {},
        "all_matches": [] 
    }
    
    wildcard_ids = set()

    for m in final_list:
        # Hide matches ended > 4 hours ago
        if NOW_MS - m['start_time'] > 14400000: continue
        
        # Format Time based on Admin Timezone
        m['fmt_time'] = format_display_time(m['start_time'], tz_str)
        m['fmt_date'] = format_display_date(m['start_time'], tz_str)
        
        # UI Elements
        m['teams_ui'] = generate_team_ui(m['title'])
        
        # Live Logic
        # Started AND not ended (> 3.5 hrs)
        m['is_live'] = (m['start_time'] <= NOW_MS) and (NOW_MS - m['start_time'] < 12600000)
        m['running_time'] = get_running_time(m['start_time']) if m['is_live'] else ""
        m['show_button'] = m['is_live'] or (m['start_time'] - NOW_MS < 1800000) # 30 min pre-game
        
        # Fake Viewers for TopEmbed matches that are Live (if Streamed.pk missed them)
        if m['viewers'] == 0 and m['is_live']:
            base = p_map.get(m['sport'], 10)
            m['viewers'] = base * 15 + int(str(m['start_time'])[-3:]) # Deterministic fake
        
        # 1. TRENDING (Live OR High Priority Starts Soon)
        score = p_map.get(m['sport'], 0)
        starts_soon = 0 < (m['start_time'] - NOW_MS) < 3600000 # 1 hour
        
        if m['is_live'] or (starts_soon and score >= 60):
            output['trending'].append(m)
            
        # 2. WILDCARD (Full Schedule)
        is_wc = wc_cat and (wc_cat == m['sport'].lower() or wc_cat == m['league'].lower())
        if is_wc:
            output['wildcard_matches'].append(m)
            wildcard_ids.add(m['id'])
            
        # 3. CATEGORIES (Standard)
        if m['id'] not in wildcard_ids:
            # Show upcoming within 24h
            if 0 < (m['start_time'] - NOW_MS) < 86400000:
                s = m['sport']
                if s not in output['categories']: output['categories'][s] = []
                output['categories'][s].append(m)

        output['all_matches'].append(m)

    # Sorting
    output['trending'].sort(key=lambda x: x.get('viewers', 0), reverse=True)
    output['wildcard_matches'].sort(key=lambda x: x['start_time'])
    
    for s in output['categories']:
        output['categories'][s].sort(key=lambda x: x['start_time'])

    return output

# ==========================================
# 5. SITE BUILDER
# ==========================================
def generate_menu_html(items, type, pages):
    html = ""
    for item in items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        # Check Highlight
        hl_style = ' style="color:var(--brand-primary);font-weight:700;"' if item.get('highlight') else ''
        
        if type == 'header':
            html += f'<a href="{url}"{hl_style}>{title}</a>'
        elif type == 'hero':
            html += f'<a href="{url}" class="cat-pill"{hl_style}>{title}</a>'
        elif type == 'footer_l':
            html += f'<a href="{url}" class="p-tag"{hl_style}>{title}</a>'
        elif type == 'footer_s':
            html += f'<a href="{url}"{hl_style}>{title}</a>'
    return html

def build_html(template, config, matches_json, page_conf):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    tgt = config.get('targeting', {})
    
    # 1. Menus
    header_html = generate_menu_html(config.get('header_menu', []), 'header', config.get('pages'))
    hero_html = generate_menu_html(config.get('hero_categories', []), 'hero', config.get('pages'))
    footer_l_html = generate_menu_html(config.get('footer_league_menu', []), 'footer_l', config.get('pages'))
    footer_s_html = generate_menu_html(config.get('footer_static_menu', []), 'footer_s', config.get('pages'))

    # 2. Replacements
    html = template
    lang = "en-US" if tgt.get('country') == "USA" else "en-GB"
    html = html.replace('lang="en"', f'lang="{lang}"')
    
    # Theme
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{STATUS}}', t.get('status_green', '#00e676'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{TREND_GRADIENT}}', t.get('trend_gradient_start', '#140000'))
    html = html.replace('{{FOOTER_BG}}', t.get('footer_bg', '#000000'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    html = html.replace('{{TITLE_C1}}', t.get('title_color_1', '#ffffff'))
    html = html.replace('{{TITLE_C2}}', t.get('title_color_2', '#D00000'))
    
    # Identity
    html = html.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    html = html.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    html = html.replace('{{SITE_NAME}}', s.get('domain', 'StreamEast'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))

    # Content
    html = html.replace('{{H1}}', page_conf.get('h1', 'Live Sports'))
    html = html.replace('{{HERO_TEXT}}', page_conf.get('hero_text', ''))
    html = html.replace('{{META_TITLE}}', page_conf.get('meta_title', ''))
    html = html.replace('{{META_DESC}}', page_conf.get('meta_desc', ''))
    html = html.replace('{{ARTICLE_CONTENT}}', page_conf.get('content', ''))

    # Menus Injection
    html = html.replace('{{HEADER_MENU}}', header_html)
    html = html.replace('{{FOOTER_STATIC_MENU}}', footer_s_html)
    html = html.replace('{{FOOTER_KEYWORDS}}', "") # Placeholder

    # Page Logic
    p_type = page_conf.get('type', 'static')
    is_home = page_conf.get('slug') == 'home'
    
    if p_type == 'static':
        html = html.replace('{{HERO_PILLS}}', '')
        html = html.replace('{{DISPLAY_SEARCH}}', 'none')
        html = html.replace('{{DISPLAY_MATCHES}}', 'none')
        html = html.replace('{{FOOTER_LEAGUE_MENU}}', '')
    else:
        html = html.replace('{{HERO_PILLS}}', hero_html)
        html = html.replace('{{DISPLAY_SEARCH}}', 'block' if is_home else 'none')
        html = html.replace('{{DISPLAY_MATCHES}}', 'block')
        html = html.replace('{{FOOTER_LEAGUE_MENU}}', footer_l_html)

    # Socials
    soc = config.get('social_stats', {})
    html = html.replace('{{SOC_TELEGRAM}}', soc.get('telegram', ''))
    html = html.replace('{{SOC_TWITTER}}', soc.get('twitter', ''))
    html = html.replace('{{SOC_DISCORD}}', soc.get('discord', ''))
    html = html.replace('{{SOC_REDDIT}}', soc.get('reddit', ''))
    html = html.replace('{{GA_CODE}}', f"<script>window.GA_ID='{s.get('ga_id')}';</script>" if s.get('ga_id') else "")
    html = html.replace('{{CUSTOM_META}}', s.get('custom_meta', ''))
    
    # JS Config
    js_config = {
        "pageType": p_type,
        "isHome": is_home,
        "category": page_conf.get('assigned_category', ''),
        "wildcard": config.get('wildcard', {}),
        "siteName": s.get('domain')
    }
    html = html.replace('//JS_CONFIG_HERE', f"window.SITE_CONFIG = {json.dumps(js_config)};")
    html = html.replace('{{STATIC_SCHEMA}}', "[]") # Placeholder

    # Path corrections
    if not is_home:
        html = html.replace('href="assets', 'href="../assets')
        html = html.replace('src="assets', 'src="../assets')
        html = html.replace('href="/', 'href="../') 
        html = html.replace('data/matches.json', '../data/matches.json')
    
    return html

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("--- 🚀 Starting Build ---")
    os.makedirs('data', exist_ok=True)
    conf = load_config()
    
    # 1. Fetch
    te_data = fetch_topembed(conf.get('api_keys', {}).get('topembed_url'))
    spk_data = fetch_streamed(conf.get('api_keys', {}).get('streamed_url'))
    
    # 2. Merge
    all_data = merge_matches(te_data, spk_data)
    
    # 3. Process
    final_json = process_data(all_data, conf)
    
    with open('data/matches.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f)
    print("✅ JSON Generated")
    
    # 4. Build Pages
    if os.path.exists('assets/master_template.html'):
        with open('assets/master_template.html', 'r', encoding='utf-8') as f:
            template = f.read()
        
        pages = conf.get('pages', [])
        if not pages: pages = [{"slug": "home", "type": "schedule"}]
        
        for p in pages:
            html = build_html(template, conf, final_json, p)
            if p.get('slug') == 'home':
                with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            else:
                slug = p['slug'].strip('/')
                os.makedirs(slug, exist_ok=True)
                with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(html)
        
        print("✅ Pages Built")
    
    print("--- ✨ Complete ---")
