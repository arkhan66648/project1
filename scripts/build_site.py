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
    country = s.get('target_country', 'US')
    html = html.replace('{{TARGET_COUNTRY}}', country)
    
    lang_code = 'en-US' 
    if country == 'UK': lang_code = 'en-GB'
    html = html.replace('lang="en"', f'lang="{lang_code}"')
    
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    domain = s.get('domain', 'example.com')
    
    # [FIX 1] Define Site Name early for use in Alt Tags and OG Data
    site_name = f"{p1}{p2}"
    html = html.replace('{{SITE_NAME}}', site_name)
    
    # [FIX 2] OG Image Logic (Absolute URL + Mime Type Detection)
    raw_logo = s.get('logo_url', '')
    og_image = ""
    og_mime = "image/png" # Default fallback
    
    if raw_logo:
        # A. Handle Absolute URL
        if raw_logo.startswith('http'):
            og_image = raw_logo
        else:
            # B. Convert relative to absolute
            clean_domain = domain[:-1] if domain.endswith('/') else domain
            clean_logo = raw_logo[1:] if raw_logo.startswith('/') else raw_logo
            if not clean_domain.startswith('http'):
                clean_domain = f"https://{clean_domain}"
            og_image = f"{clean_domain}/{clean_logo}"
            
        # C. Detect MIME Type (WebP Support)
        low_img = og_image.lower()
        if low_img.endswith('.webp'):
            og_mime = "image/webp"
        elif low_img.endswith('.jpg') or low_img.endswith('.jpeg'):
            og_mime = "image/jpeg"
        elif low_img.endswith('.gif'):
            og_mime = "image/gif"
        else:
            og_mime = "image/png"

    html = html.replace('{{OG_IMAGE}}', og_image)
    html = html.replace('{{OG_MIME}}', og_mime)

    # [FIX 3] Add ALT Tag to Logo
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'): 
        # Added alt="{site_name} Logo" here
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img" alt="{site_name} Logo" fetchpriority="high"> {logo_html}'
        
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

    html = html.replace('{{ENTITY_SECTION}}', '')
    
    # --- 4. SEO & Metadata ---
    html = html.replace('{{META_TITLE}}', page_data.get('meta_title') or f"{p1}{p2} - {page_data.get('title')}")
    html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
    
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
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    html = html.replace('{{ARTICLE_CONTENT}}', page_data.get('content', ''))

    # --- 6. JS Injections ---
    priorities = config.get('sport_priorities', {}).get(country, {})
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))
    
    social_data = config.get('social_sharing', {})
    excluded_str = social_data.get('excluded_pages', '')
    excluded_list = [x.strip() for x in excluded_str.split(',') if x.strip()]
    
    js_social_object = {
        "excluded": excluded_list,
        "counts": social_data.get('counts', {})
    }
    
    social_json = json.dumps(js_social_object)
    html = re.sub(r'const SHARE_CONFIG = \{.*?\};', f'const SHARE_CONFIG = {social_json};', html, flags=re.DOTALL)

    # --- 7. STATIC SCHEMA GENERATION ---
    schemas = []
    page_schemas = page_data.get('schemas', {})

    if page_schemas.get('org'):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": f"https://{domain}/#organization",
            "name": f"{p1}{p2}",
            "url": f"https://{domain}/",
            "logo": {
                "@type": "ImageObject",
                "url": s.get('logo_url')
            }
        })

    if page_schemas.get('website'):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": f"https://{domain}/#website",
            "url": f"https://{domain}/",
            "name": f"{p1}{p2}",
            "publisher": {
                "@type": "Organization",
                "@id": f"https://{domain}/#organization"
            }
        })

    if page_schemas.get('faq'):
        faq_list = page_schemas.get('faq_list', [])
        valid_faqs = []
        for item in faq_list:
            if item.get('q') and item.get('a'):
                valid_faqs.append({
                    "@type": "Question",
                    "name": item.get('q'),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item.get('a')
                    }
                })
        
        if valid_faqs:
            schemas.append({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": valid_faqs
            })

    if schemas:
        schema_html = f'<script type="application/ld+json">{json.dumps(schemas)}</script>'
        html = html.replace('{{SCHEMA_BLOCK}}', schema_html)
    else:
        html = html.replace('{{SCHEMA_BLOCK}}', '')
        preload_html = ""
    if s.get('logo_url'):
        preload_html = f'<link rel="preload" as="image" href="{s.get("logo_url")}" fetchpriority="high">'
    html = html.replace('{{LOGO_PRELOAD}}', preload_html)

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
            # Creates folder based on slug (e.g. /nba-streams/index.html)
            dir_path = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(dir_path, exist_ok=True)
            out_path = os.path.join(dir_path, 'index.html')
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

    print("✅ Build Complete (Auto-Generation Stopped)")

if __name__ == "__main__":
    build_site()
