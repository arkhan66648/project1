import json
import os
import time
import re
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone as ZoneInfo

NOW_MS = int(time.time() * 1000)
TEAM_COLORS = ["#D00000", "#0056D2", "#008f39", "#7C3AED", "#FFD700", "#ff5722", "#00bcd4", "#e91e63"]

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

# --- MENU GENERATOR ---
def generate_menu_html(items, type, pages):
    html = ""
    for item in items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        hl_style = ' style="color:var(--brand-primary);font-weight:700;"' if item.get('highlight') else ''
        
        if type == 'header': html += f'<a href="{url}"{hl_style}>{title}</a>'
        elif type == 'hero': html += f'<a href="{url}" class="cat-pill"{hl_style}>{title}</a>'
        elif type == 'footer_l': html += f'<a href="{url}" class="p-tag"{hl_style}>{title}</a>'
        elif type == 'footer_s': html += f'<a href="{url}"{hl_style}>{title}</a>'
    return html

# --- MATCH UI GENERATORS ---
def generate_team_ui(title):
    teams = []
    # Logic to split "A vs B"
    parts = re.split(r'\s+vs\.?\s+|\s+-\s+|\s+v\s+', title)
    for name in parts[:2]:
        clean = name.strip()
        if clean:
            # Deterministic Color based on name length/content
            val = sum(ord(c) for c in clean)
            teams.append({"name": clean, "letter": clean[0].upper(), "color": TEAM_COLORS[val % 8]})
    return teams

def create_match_html(m, timezone_str):
    # 1. Handle Timezone Conversion
    try:
        # Defaults to 'US/Eastern' if invalid, handled by fallback
        tz = ZoneInfo(timezone_str)
        dt = datetime.fromtimestamp(m['start_time'] / 1000, tz)
        fmt_time = dt.strftime('%I:%M %p').lstrip('0') # e.g., 7:00 PM
        fmt_date = dt.strftime('%b %d')                # e.g., Jan 01
    except:
        # Fallback if timezone library fails
        dt = datetime.fromtimestamp(m['start_time'] / 1000)
        fmt_time = dt.strftime('%I:%M %p').lstrip('0')
        fmt_date = dt.strftime('%b %d')

    # 2. Live Status Logic
    # Match is LIVE if start_time is passed AND it started less than 4 hours ago
    is_live = (m['start_time'] <= NOW_MS) and (NOW_MS - m['start_time'] < 14400000)
    
    # 3. Build Columns
    col1 = ""
    if is_live:
        runtime = (NOW_MS - m['start_time']) // 60000
        time_display = f"{runtime}'" if runtime < 180 else "FT"
        col1 = f'<span class="live-txt">LIVE</span><span class="time-sub" style="color:#fff">{time_display}</span>'
    else:
        col1 = f'<span class="time-main">{fmt_time}</span><span class="time-sub">{fmt_date}</span>'

    teams = generate_team_ui(m['title'])
    teams_html = ""
    if teams:
        for t in teams:
            teams_html += f'<div class="team-name"><span class="t-circle" style="background:{t["color"]}">{t["letter"]}</span>{t["name"]}</div>'
    else:
        teams_html = f'<div class="team-name">{m["title"]}</div>'
        
    league_tag = f'<div class="league-tag">{m["league"]}</div>'

    # 4. Button Logic
    btn = ""
    # Show Watch button if Live OR starting in 30 mins
    if is_live or (m['start_time'] - NOW_MS < 1800000):
        # Viewers logic (fake if missing)
        v = m.get('viewers', 0)
        if v == 0 and is_live: v = 1500
        
        link_id = m['streams'][0]['id'] if m['streams'] else ""
        title_safe = m['title'].replace("'", "")
        btn = f'<div class="meta-top">⚡ {v}</div><button class="btn-watch" onclick="openPlayer(\'{m["id"]}\', \'{link_id}\', \'{title_safe}\')">WATCH</button>'
    else:
        btn = f'<div class="meta-top"><span class="countdown" data-time="{m["start_time"]}">--:--</span></div><button class="btn-watch btn-notify" onclick="toggleNotify(this)">🔔 Notify</button>'

    # 5. Full Row HTML
    return f"""
    <div class="match-row {'live' if is_live else ''}" data-search="{m['title'].lower()} {m['league'].lower()}">
        <div class="col-time">{col1}</div>
        <div class="col-info">{league_tag}{teams_html}</div>
        <div class="col-meta">{btn}</div>
    </div>
    """

def build_site():
    print("--- 🔨 Building Site ---")
    config = load_json('data/config.json')
    matches = load_json('data/matches_raw.json')
    
    # Settings
    tgt_tz = config.get('targeting', {}).get('timezone', 'US/Eastern')
    priorities = config.get('sport_priorities', {})
    
    # Filter Data
    matches_live = []
    matches_upcoming = {}
    matches_wildcard = []
    wc_cat = config.get('wildcard', {}).get('category', '').lower()

    for m in matches:
        # Skip old matches (>4h ago)
        if NOW_MS - m['start_time'] > 14400000: continue
        
        # Check Live
        is_live = (m['start_time'] <= NOW_MS)
        
        # 1. Trending/Live
        # Add if Live OR (Starts < 1h AND Priority > 50)
        p_score = priorities.get(m['sport'], 50)
        starts_soon = (m['start_time'] - NOW_MS < 3600000)
        
        if is_live or (starts_soon and p_score > 60):
            matches_live.append(m)
        
        # 2. Upcoming Schedule (Non-Live)
        if not is_live:
            s = m['sport']
            if s not in matches_upcoming: matches_upcoming[s] = []
            matches_upcoming[s].append(m)
            
        # 3. Wildcard
        if wc_cat and (wc_cat == m['sport'].lower() or wc_cat == m['league'].lower()):
            matches_wildcard.append(m)

    # Sort Live by Viewers
    matches_live.sort(key=lambda x: x.get('viewers', 0), reverse=True)

    # --- GENERATE HTML BLOCKS ---
    
    # Block 1: Trending
    if matches_live:
        rows = "".join([create_match_html(m, tgt_tz) for m in matches_live])
        html_live = rows
    else:
        html_live = '<div style="padding:20px;text-align:center;color:#666">No matches right now.</div>'

    # Block 2: Wildcard
    html_wildcard = ""
    if matches_wildcard:
        matches_wildcard.sort(key=lambda x: x['start_time'])
        rows = "".join([create_match_html(m, tgt_tz) for m in matches_wildcard])
        html_wildcard = f"""
        <div class="sec-head" id="{config.get('wildcard',{}).get('id','wc')}">
            <div class="sec-title">🔥 {config.get("wildcard", {}).get("category", "Featured")}</div>
        </div>
        <div class="match-list">{rows}</div>
        """

    # Block 3: Upcoming Categories (SORTED BY PRIORITY)
    html_upcoming = ""
    # Get sports list and sort by Admin Priority Score (Desc)
    sorted_sports = sorted(matches_upcoming.keys(), key=lambda k: priorities.get(k, 50), reverse=True)
    
    for sport in sorted_sports:
        ms = matches_upcoming[sport]
        if not ms: continue
        ms.sort(key=lambda x: x['start_time'])
        
        # Take top 4
        rows = "".join([create_match_html(m, tgt_tz) for m in ms[:4]])
        
        html_upcoming += f"""
        <div class="sport-section" data-sport="{sport}">
            <div class="sec-head">
                <div class="sec-title">{sport} Schedule</div>
                <a href="/{sport.lower().replace(' ','-')}/" class="sec-right-link">View All ></a>
            </div>
            <div class="match-list">{rows}</div>
        </div>
        """

    # --- TEMPLATE REPLACEMENT ---
    if not os.path.exists('assets/master_template.html'):
        print("❌ Template not found")
        return

    with open('assets/master_template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    # Theme CSS
    t = config.get('theme', {})
    template = template.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    template = template.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    template = template.replace('{{ACCENT}}', t.get('accent_gold', '#FFD700'))
    template = template.replace('{{STATUS}}', t.get('status_green', '#00e676'))
    template = template.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    template = template.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    template = template.replace('{{TREND_GRADIENT}}', t.get('trend_gradient_start', '#140000'))
    template = template.replace('{{FOOTER_BG}}', t.get('footer_bg', '#000000'))
    template = template.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    template = template.replace('{{TITLE_C1}}', t.get('title_color_1', '#ffffff'))
    template = template.replace('{{TITLE_C2}}', t.get('title_color_2', '#D00000'))
    
    # Site Identity
    s = config.get('site_settings', {})
    template = template.replace('{{TITLE_P1}}', s.get('title_part_1', 'Stream'))
    template = template.replace('{{TITLE_P2}}', s.get('title_part_2', 'East'))
    template = template.replace('{{SITE_NAME}}', s.get('domain', 'StreamEast'))
    template = template.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    template = template.replace('{{FAVICON}}', s.get('favicon', ''))
    template = template.replace('{{DOMAIN}}', s.get('domain', ''))
    template = template.replace('{{GA_CODE}}', f"<script>window.GA_ID='{s.get('ga_id')}';</script>" if s.get('ga_id') else "")
    template = template.replace('{{CUSTOM_META}}', s.get('custom_meta', ''))
    
    # Socials
    soc = config.get('social_stats', {})
    template = template.replace('{{SOC_TELEGRAM}}', soc.get('telegram', ''))
    template = template.replace('{{SOC_TWITTER}}', soc.get('twitter', ''))
    template = template.replace('{{SOC_DISCORD}}', soc.get('discord', ''))
    template = template.replace('{{SOC_REDDIT}}', soc.get('reddit', ''))
    
    # Menus
    pages_conf = config.get('pages', [])
    template = template.replace('{{HEADER_MENU}}', generate_menu_html(config.get('header_menu', []), 'header', pages_conf))
    template = template.replace('{{HERO_PILLS}}', generate_menu_html(config.get('hero_categories', []), 'hero', pages_conf))
    template = template.replace('{{FOOTER_LEAGUE_MENU}}', generate_menu_html(config.get('footer_league_menu', []), 'footer_l', pages_conf))
    template = template.replace('{{FOOTER_STATIC_MENU}}', generate_menu_html(config.get('footer_static_menu', []), 'footer_s', pages_conf))
    
    # JS Config (Minimal now)
    js_conf = {"siteName": s.get('domain'), "timezone": tgt_tz}
    template = template.replace('//JS_CONFIG_HERE', f"window.SITE_CONFIG = {json.dumps(js_conf)};")
    template = template.replace('{{STATIC_SCHEMA}}', "[]")
    
    # --- FIX: LIST JOIN ERROR ---
    kw_list = s.get('footer_keywords', [])
    kw_str = ', '.join(kw_list) if isinstance(kw_list, list) else ""
    template = template.replace('{{FOOTER_KEYWORDS}}', kw_str)

    # --- PAGE GENERATION ---
    if not pages_conf: pages_conf = [{"slug": "home", "type": "schedule"}]

    for p in pages_conf:
        html = template
        html = html.replace('{{H1}}', p.get('h1', 'Live Sports'))
        html = html.replace('{{HERO_TEXT}}', p.get('hero_text', ''))
        html = html.replace('{{META_TITLE}}', p.get('meta_title', ''))
        html = html.replace('{{META_DESC}}', p.get('meta_desc', ''))
        html = html.replace('{{ARTICLE_CONTENT}}', p.get('content', ''))

        if p.get('slug') == 'home':
            html = html.replace('{{DISPLAY_SEARCH}}', 'block')
            html = html.replace('{{DISPLAY_MATCHES}}', 'block')
            
            # INJECT MATCHES INTO HTML
            # We target the ID divs
            html = html.replace('<div id="live-matches-container" class="match-list">', f'<div id="live-matches-container" class="match-list">{html_live}')
            html = html.replace('<div id="wildcard-wrapper"></div>', f'<div id="wildcard-wrapper">{html_wildcard}</div>')
            html = html.replace('<div id="upcoming-wrapper"></div>', f'<div id="upcoming-wrapper">{html_upcoming}</div>')
            
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
        
        else:
            # Subpages
            slug = p['slug'].strip('/')
            os.makedirs(slug, exist_ok=True)
            
            html = html.replace('{{DISPLAY_SEARCH}}', 'none')
            
            if p.get('type') == 'static':
                html = html.replace('{{DISPLAY_MATCHES}}', 'none')
            else:
                # Category Page (e.g. /nfl/)
                html = html.replace('{{DISPLAY_MATCHES}}', 'block')
                # Inject only specific category matches
                cat_filter = p.get('assigned_category', '').lower()
                
                # Filter Logic for Category Page
                cat_html = ""
                if cat_filter and cat_filter in matches_upcoming.keys():
                    # Find key case insensitive
                    key = next((k for k in matches_upcoming.keys() if k.lower() == cat_filter), None)
                    if key:
                        rows = "".join([create_match_html(m, tgt_tz) for m in matches_upcoming[key]])
                        cat_html = f'<div class="match-list">{rows}</div>'
                
                html = html.replace('<div id="upcoming-wrapper"></div>', f'<div id="upcoming-wrapper">{cat_html}</div>')
                # Clear others
                html = html.replace('<div id="live-matches-container" class="match-list">', '<div id="live-matches-container" class="match-list" style="display:none">')
                html = html.replace('<div id="wildcard-wrapper"></div>', '')

            # Path Fixes
            html = html.replace('href="assets', 'href="../assets')
            html = html.replace('src="assets', 'src="../assets')
            html = html.replace('href="/', 'href="../')

            with open(f"{slug}/index.html", 'w', encoding='utf-8') as f: f.write(html)

    print(f"✅ Site Built using timezone: {tgt_tz}")

if __name__ == "__main__":
    build_site()
