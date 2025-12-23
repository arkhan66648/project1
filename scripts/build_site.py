import json
import os
import re

CONFIG_PATH = 'data/config.json'
TEMPLATE_PATH = 'assets/master_template.html'
OUTPUT_DIR = '.' 

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def build_menu_html(menu_items, section):
    html = ""
    for item in menu_items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        
        # Req #2: Header Menu Highlight
        if section == 'header':
            # Check if highlight is enabled in admin
            style = ' style="color:#facc15; border-bottom:1px solid #facc15;"' if item.get('highlight') else ''
            html += f'<a href="{url}"{style}>{title}</a>'
            
        # Req #4: Professional Footer Leagues
        elif section == 'footer_leagues':
            # Auto-assign icons based on keyword (fallback to trophy)
            icon = "🏆"
            t_low = title.lower()
            if "soccer" in t_low or "premier" in t_low: icon = "⚽"
            elif "nba" in t_low or "basket" in t_low: icon = "🏀"
            elif "nfl" in t_low or "football" in t_low: icon = "🏈"
            elif "mlb" in t_low or "baseball" in t_low: icon = "⚾"
            elif "ufc" in t_low or "boxing" in t_low: icon = "🥊"
            elif "f1" in t_low or "motor" in t_low: icon = "🏎️"
            
            # Preserves your specific League Card HTML structure
            html += f'''
            <a href="{url}" class="league-card">
                <span class="l-icon">{icon}</span>
                <span>{title}</span>
            </a>'''
            
        # Hero Pills
        elif section == 'hero':
            html += f'<a href="{url}" class="cat-pill">{title}</a>'
            
        # Footer Static Links
        elif section == 'footer_static':
             html += f'<a href="{url}" class="f-link">{title}</a>'
        
        # Fallback
        else:
            html += f'<a href="{url}">{title}</a>'
            
    return html

def generate_entity_footer(entities):
    # Req #5: Trusted Partners (Entity Stacking)
    if not entities: return ""
    html = ""
    for item in entities:
        kw = item.get('keyword', '').replace('"', '&quot;')
        # Generates buttons that trigger the overlay defined in the template
        html += f'<button class="p-tag" onclick="triggerEntityPopup(\'{kw}\')">{kw}</button>'
    return html

def render_page(template, config, page_data):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    m = config.get('menus', {})
    
    html = template
    
    # --- 1. Basic Config & Theme ---
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    
    # Req #1: Target Country & Lang
    # Strict Logic for US/UK Admin Panel Options
    country = s.get('target_country', 'US')
    html = html.replace('{{TARGET_COUNTRY}}', country)
    
    lang_code = 'en-US' # Default
    if country == 'UK':
        lang_code = 'en-GB'
    
    # Update HTML tag
    html = html.replace('lang="en"', f'lang="{lang_code}"')
    
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    domain = s.get('domain', 'example.com')
    
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'): logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{DOMAIN}}', domain)
    html = html.replace('{{FAVICON}}', s.get('favicon_url', ''))

    # --- 2. Menus ---
    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', []), 'header'))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), 'hero'))
    html = html.replace('{{FOOTER_LEAGUES}}', build_menu_html(m.get('footer_leagues', []), 'footer_leagues'))
    html = html.replace('{{FOOTER_STATIC}}', build_menu_html(m.get('footer_static', []), 'footer_static'))
    
    # --- 3. Footer Content ---
    html = html.replace('{{FOOTER_COPYRIGHT}}', s.get('footer_copyright', f"&copy; 2025 {domain}"))
    
    disclaimer = s.get('footer_disclaimer', '')
    if disclaimer: html = html.replace('{{FOOTER_DISCLAIMER}}', f'{disclaimer}')
    else: html = html.replace('{{FOOTER_DISCLAIMER}}', '')

    html = html.replace('{{ENTITY_SECTION}}', generate_entity_footer(config.get('entity_stacking', [])))
    
    # --- 4. SEO & Metadata ---
    html = html.replace('{{META_TITLE}}', page_data.get('meta_title') or f"{p1}{p2} - {page_data.get('title')}")
    html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
    
    # Req #7: Meta Keywords Fix
    keywords = page_data.get('meta_keywords', '')
    if keywords: html = html.replace('{{META_KEYWORDS}}', f'<meta name="keywords" content="{keywords}">')
    else: html = html.replace('{{META_KEYWORDS}}', '')

    canon = page_data.get('canonical_url', '')
    if not canon: canon = f"https://{domain}/{page_data.get('slug', '')}"
    html = html.replace('{{CANONICAL_URL}}', canon)

    html = html.replace('{{H1_TITLE}}', page_data.get('title', ''))
    html = html.replace('{{HERO_TEXT}}', page_data.get('hero_text') or page_data.get('meta_desc', ''))

    # --- 5. Layout Logic ---
    layout = page_data.get('layout', 'page')
    if layout == 'home':
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    else:
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        # Inject CSS to hide live sections on subpages (Critical for SEO pages)
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    html = html.replace('{{ARTICLE_CONTENT}}', page_data.get('content', ''))

    # --- 6. JS Injections (Priorities, Socials, Schemas) ---
    
    # Priorities Injection
    # This automatically handles the new "_HIDE_OTHERS" key from Admin/Config 
    # because it dumps the entire dictionary for that country.
    priorities = config.get('sport_priorities', {}).get(country, {})
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))
    
    # Req #9: Social Sharing Config
    social_data = config.get('social_sharing', {})
    
    # We parse the excluded string into a list
    excluded_str = social_data.get('excluded_pages', '')
    excluded_list = [x.strip() for x in excluded_str.split(',') if x.strip()]
    
    js_social_object = {
        "excluded": excluded_list,
        "counts": social_data.get('counts', {})
    }
    
    # Regex to replace the default SHARE_CONFIG in template with dynamic one
    # This uses re.DOTALL to ensure it catches multiline JS objects
    social_json = json.dumps(js_social_object)
    html = re.sub(r'const SHARE_CONFIG = \{.*?\};', f'const SHARE_CONFIG = {social_json};', html, flags=re.DOTALL)

    # --- 7. Schemas ---
    # A. Static Org Schema
    schemas = []
    if page_data.get('schemas', {}).get('org'):
        schemas.append({
            "@context": "https://schema.org", "@type": "Organization",
            "name": f"{p1}{p2}", "url": f"https://{domain}", "logo": s.get('logo_url')
        })
    
    if schemas: html = html.replace('{{SCHEMA_BLOCK}}', f'<script type="application/ld+json">{json.dumps(schemas)}</script>')
    else: html = html.replace('{{SCHEMA_BLOCK}}', '')

    # B. Dynamic Schema Control (Req #8)
    # We inject a variable so frontend knows if it's allowed to inject Live/Schedule schemas
    enable_live_schema = "true" if page_data.get('schemas', {}).get('live') else "false"
    enable_schedule_schema = "true" if page_data.get('schemas', {}).get('schedule') else "false"
    
    # We prepend this config to the API URL definition in the script
    # This is a robust way to add config without breaking the template's structure
    schema_config_js = f'const ENABLE_SCHEMAS = {{ live: {enable_live_schema}, schedule: {enable_schedule_schema} }};\n        const API_URL'
    html = html.replace('const API_URL', schema_config_js)

    return html

def build_site():
    print("--- 🔨 Starting Build Process ---")
    config = load_json(CONFIG_PATH)
    if not config: 
        print("❌ Config not found!")
        return

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    print("📄 Building Pages...")
    for page in config.get('pages', []):
        slug = page.get('slug')
        final_html = render_page(template, config, page)
        
        # Folder Generation Logic
        if slug == 'home':
            out_path = os.path.join(OUTPUT_DIR, 'index.html')
        else:
            # This handles your new requirement: 
            # If you create a page with slug "nba-streams" in Admin, 
            # this correctly creates folder "nba-streams" and index.html inside it.
            dir_path = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(dir_path, exist_ok=True)
            out_path = os.path.join(dir_path, 'index.html')
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

    print("✅ Build Complete (Auto-Generation Stopped)")

if __name__ == "__main__":
    build_site()
