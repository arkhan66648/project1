import json
import time
import requests
import os
import base64
import sys
import hashlib
import re
from datetime import datetime, timedelta

# Try to import ZoneInfo for timezone handling (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone as ZoneInfo

NOW_MS = int(time.time() * 1000)

PRIORITY_USA = { "NFL": 100, "NBA": 95, "UFC": 90, "MLB": 85, "NHL": 80, "NCAA Football": 75, "NCAA Basketball": 70, "Soccer": 60, "F1": 50, "Boxing": 70, "Tennis": 40, "Golf": 30 }
PRIORITY_UK = { "Soccer": 100, "Boxing": 95, "F1": 90, "Tennis": 85, "Cricket": 80, "NFL": 70, "NBA": 60, "UFC": 75, "Rugby": 70, "Golf": 50 }
TEAM_COLORS = ["#D00000", "#0056D2", "#008f39", "#7C3AED", "#FFD700", "#ff5722", "#00bcd4", "#e91e63"]

def load_config():
    if not os.path.exists('data/config.json'): return {}
    try:
        with open('data/config.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def obfuscate_link(link):
    if not link: return ""
    return base64.b64encode(link.encode('utf-8')).decode('utf-8')

def clean_channel_name(raw_url):
    try:
        if '[' in raw_url:
            parts = raw_url.split('/channel/')
            if len(parts) > 1: return parts[1].split('[')[0].replace('-', ' ').upper()
    except: pass
    return "HD STREAM"

def get_robust_id(title, start_time_ms):
    separator = ' vs ' if ' vs ' in title else ' - '
    teams = title.split(separator)
    teams.sort()
    clean_teams = "".join([t.lower().strip() for t in teams])
    date_str = datetime.fromtimestamp(start_time_ms / 1000).strftime('%Y%m%d')
    return hashlib.md5(f"{clean_teams}_{date_str}".encode('utf-8')).hexdigest()

def detect_sport_normalized(raw_sport, raw_league):
    s, l = raw_sport.upper(), raw_league.upper()
    if "BASKETBALL" in s: return "NCAA Basketball" if "COLLEGE" in l or "NCAA" in l else ("NBA" if "NBA" in l else "Basketball")
    if "FOOTBALL" in s or "AMERICAN FOOTBALL" in s: return "NCAA Football" if "COLLEGE" in l or "NCAA" in l else ("NFL" if "NFL" in l else "American Football")
    if "HOCKEY" in s: return "NHL" if "NHL" in l else "Ice Hockey"
    if "BASEBALL" in s: return "MLB" if "MLB" in l else "Baseball"
    if "SOCCER" in s: return "Soccer"
    if "FIGHT" in s or "MMA" in s or "UFC" in s: return "UFC"
    if "BOXING" in s: return "Boxing"
    if "RACING" in s or "F1" in s: return "F1"
    return raw_sport.title()

def generate_team_ui(title):
    teams = []
    parts = re.split(r'\s+vs\.?\s+|\s+-\s+', title)
    if len(parts) >= 2:
        for name in parts[:2]:
            clean = name.strip()
            letter = clean[0].upper() if clean else "X"
            color = TEAM_COLORS[int(hashlib.md5(clean.encode('utf-8')).hexdigest(), 16) % len(TEAM_COLORS)]
            teams.append({"name": clean, "letter": letter, "color": color})
    return teams

def get_running_time(start_ms):
    diff = (NOW_MS - start_ms) // 60000
    if diff < 0: return "Pre"
    if diff > 180: return "FT"
    return f"{diff}'"

def format_display_time(ts_ms, timezone_str):
    try:
        return datetime.fromtimestamp(ts_ms / 1000, ZoneInfo(timezone_str)).strftime('%I:%M %p').lstrip('0')
    except: return "--:--"

def format_display_date(ts_ms, timezone_str):
    try:
        return datetime.fromtimestamp(ts_ms / 1000, ZoneInfo(timezone_str)).strftime('%b %d')
    except: return ""

def fetch_topembed(url):
    matches = []
    if not url: return matches
    print(f"Fetching TopEmbed: {url}")
    try:
        data = requests.get(url, timeout=15).json()
        events_map = data.get('events', {})
        for date_key, event_list in events_map.items():
            for ev in event_list:
                try: start_ms = int(ev['unixTimestamp']) * 1000
                except: continue
                title = ev.get('match', 'Unknown Match')
                sport = detect_sport_normalized(ev.get('sport', 'Other'), ev.get('tournament', ''))
                league = ev.get('tournament', '') or sport
                
                streams = []
                channels = ev.get('channels', [])
                if isinstance(channels, list):
                    for ch in channels:
                        if isinstance(ch, str): link = ch
                        elif isinstance(ch, dict): link = ch.get('channel', '')
                        if link: streams.append({"id": obfuscate_link(link), "name": clean_channel_name(link), "source": "te"})

                matches.append({"id": get_robust_id(title, start_ms), "title": title, "sport": sport, "league": league, "start_time": start_ms, "viewers": 0, "streams": streams})
    except Exception as e: print(f"❌ TopEmbed Error: {e}")
    return matches

def fetch_streamed(url):
    matches = []
    if not url: return matches
    print(f"Fetching Streamed: {url}")
    try:
        data = requests.get(url, timeout=15).json()
        for m in data:
            try: start_ms = int(m.get('date', 0))
            except: start_ms = NOW_MS + 3600000
            title = m.get('title', 'Unknown')
            sport = detect_sport_normalized(m.get('category', 'Other'), title)
            streams = []
            for src in m.get('sources', []):
                link = src.get('url') or src.get('id') or ""
                streams.append({"id": obfuscate_link(link), "name": src.get('source', 'Stream'), "source": "spk"})
            matches.append({"id": get_robust_id(title, start_ms), "title": title, "sport": sport, "league": sport, "start_time": start_ms, "viewers": int(m.get('viewers', 0)), "streams": streams})
    except Exception as e: print(f"❌ Streamed Error: {e}")
    return matches

def merge_matches(list1, list2):
    master = {}
    for m in list1: master[m['id']] = m
    for m in list2:
        mid = m['id']
        if mid in master:
            existing = master[mid]
            existing['streams'].extend(m['streams'])
            if m['viewers'] > existing['viewers']: existing['viewers'] = m['viewers']
            if existing['league'] == 'Other' and m['league'] != 'Other': existing['league'] = m['league']
        else: master[mid] = m
    return list(master.values())

def process_data(matches, config):
    tgt = config.get('targeting', {})
    country = tgt.get('country', 'USA')
    tz_str = tgt.get('timezone', 'US/Eastern')
    p_map = PRIORITY_UK if country == 'UK' else PRIORITY_USA
    wc_conf = config.get('wildcard', {})
    wc_cat = wc_conf.get('category', '').lower()
    
    output = { "trending": [], "wildcard_matches": [], "categories": {}, "all_matches": [] }
    wildcard_ids = set()

    for m in matches:
        if NOW_MS - m['start_time'] > 10800000: continue
        m['fmt_time'] = format_display_time(m['start_time'], tz_str)
        m['fmt_date'] = format_display_date(m['start_time'], tz_str)
        m['teams_ui'] = generate_team_ui(m['title'])
        m['is_live'] = (m['start_time'] <= NOW_MS) and (NOW_MS - m['start_time'] < 10800000)
        m['running_time'] = get_running_time(m['start_time']) if m['is_live'] else ""
        m['show_button'] = m['is_live'] or (m['start_time'] - NOW_MS < 1800000)
        
        if m['viewers'] == 0 and m['is_live']:
            m['viewers'] = p_map.get(m['sport'], 10) * 12 + int(str(m['start_time'])[-3:])
        
        score = p_map.get(m['sport'], 0)
        if m['is_live'] or (0 < (m['start_time'] - NOW_MS) < 3600000 and score >= 70):
            output['trending'].append(m)
            
        if wc_cat and (wc_cat == m['sport'].lower() or wc_cat == m['league'].lower()):
            output['wildcard_matches'].append(m)
            wildcard_ids.add(m['id'])
            
        if m['id'] not in wildcard_ids and 0 < (m['start_time'] - NOW_MS) < 86400000:
            s = m['sport']
            if s not in output['categories']: output['categories'][s] = []
            output['categories'][s].append(m)
        output['all_matches'].append(m)

    output['trending'].sort(key=lambda x: x.get('viewers', 0), reverse=True)
    output['wildcard_matches'].sort(key=lambda x: x['start_time'])
    for s in output['categories']: output['categories'][s].sort(key=lambda x: x['start_time'])
    return output

def generate_menu_html(items, type, pages):
    html = ""
    for item in items:
        title, url = item.get('title', 'Link'), item.get('url', '#')
        hl = ' style="color:var(--brand-primary);font-weight:bold;"' if item.get('highlight') else ''
        cls = "cat-pill" if type == 'hero' else ("p-tag" if type == 'footer_l' else "")
        html += f'<a href="{url}" class="{cls}"{hl}>{title}</a>'
    return html

def build_html(template, config, matches_json, page_conf):
    s, t, tgt = config.get('site_settings', {}), config.get('theme', {}), config.get('targeting', {})
    lang = "en-US" if tgt.get('country') == "USA" else "en-GB"
    
    html = template.replace('lang="en"', f'lang="{lang}"')
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
    
    html = html.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    html = html.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    html = html.replace('{{SITE_NAME}}', s.get('domain', 'StreamEast'))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))
    
    html = html.replace('{{H1}}', page_conf.get('h1', 'Live Sports'))
    html = html.replace('{{HERO_TEXT}}', page_conf.get('hero_text', ''))
    html = html.replace('{{META_TITLE}}', page_conf.get('meta_title', ''))
    html = html.replace('{{META_DESC}}', page_conf.get('meta_desc', ''))
    html = html.replace('{{ARTICLE_CONTENT}}', page_conf.get('content', ''))
    
    html = html.replace('{{HEADER_MENU}}', generate_menu_html(config.get('header_menu', []), 'header', []))
    html = html.replace('{{FOOTER_STATIC_MENU}}', generate_menu_html(config.get('footer_static_menu', []), 'footer_s', []))
    
    # Footer Keywords (Network)
    kw_html = ""
    for k in s.get('footer_keywords', []):
        if k: kw_html += f'<a href="/?q={k.strip()}" class="p-tag">{k.strip()}</a>'
    html = html.replace('{{FOOTER_KEYWORDS}}', kw_html)

    if page_conf.get('type') == 'static':
        html = html.replace('{{HERO_PILLS}}', '').replace('{{DISPLAY_SEARCH}}', 'none').replace('{{DISPLAY_MATCHES}}', 'none').replace('{{FOOTER_LEAGUE_MENU}}', '')
    else:
        html = html.replace('{{HERO_PILLS}}', generate_menu_html(config.get('hero_categories', []), 'hero', []))
        html = html.replace('{{DISPLAY_SEARCH}}', 'block' if page_conf.get('slug')=='home' else 'none')
        html = html.replace('{{DISPLAY_MATCHES}}', 'block')
        html = html.replace('{{FOOTER_LEAGUE_MENU}}', generate_menu_html(config.get('footer_league_menu', []), 'footer_l', []))

    soc = config.get('social_stats', {})
    html = html.replace('{{SOC_TELEGRAM}}', soc.get('telegram', ''))
    html = html.replace('{{SOC_TWITTER}}', soc.get('twitter', ''))
    html = html.replace('{{SOC_DISCORD}}', soc.get('discord', ''))
    html = html.replace('{{SOC_REDDIT}}', soc.get('reddit', ''))
    html = html.replace('{{GA_CODE}}', f"<script>window.GA_ID='{s.get('ga_id')}';</script>" if s.get('ga_id') else "")
    html = html.replace('{{CUSTOM_META}}', s.get('custom_meta', ''))
    
    js_config = { "pageType": page_conf.get('type'), "isHome": page_conf.get('slug')=='home', "category": page_conf.get('assigned_category'), "wildcard": config.get('wildcard'), "siteName": s.get('domain') }
    html = html.replace('//JS_CONFIG_HERE', f"window.SITE_CONFIG = {json.dumps(js_config)};")
    html = html.replace('{{STATIC_SCHEMA}}', "[]")

    if page_conf.get('slug') != 'home':
        html = html.replace('href="assets', 'href="../assets').replace('src="assets', 'src="../assets').replace('href="/', 'href="../').replace('data/matches.json', '../data/matches.json')
    return html

if __name__ == "__main__":
    print("--- 🚀 Starting Build ---")
    os.makedirs('data', exist_ok=True)
    conf = load_config()
    raw = merge_matches(fetch_topembed(conf.get('api_keys', {}).get('topembed_url')), fetch_streamed(conf.get('api_keys', {}).get('streamed_url')))
    final = process_data(raw, conf)
    with open('data/matches.json', 'w', encoding='utf-8') as f: json.dump(final, f)
    
    if os.path.exists('assets/master_template.html'):
        with open('assets/master_template.html', 'r', encoding='utf-8') as f: template = f.read()
        pages = conf.get('pages', []) or [{"slug": "home", "type": "schedule"}]
        for p in pages:
            html = build_html(template, conf, final, p)
            if p.get('slug') == 'home': 
                with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            else:
                slug = p['slug'].strip('/')
                os.makedirs(slug, exist_ok=True)
                with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(html)
    print("--- ✨ Complete ---")
