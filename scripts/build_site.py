import json
import os
import re

# ==========================================
# 1. CONFIGURATION
# ==========================================
CONFIG_PATH = 'data/config.json'
LEAGUE_MAP_PATH = 'assets/data/league_map.json' 
IMAGE_MAP_PATH = 'assets/data/image_map.json'  # Added
TEMPLATE_PATH = 'assets/master_template.html'
WATCH_TEMPLATE_PATH = 'assets/watch_template.html' 
OUTPUT_DIR = '.' 

# ==========================================
# 2. UTILS
# ==========================================
def load_json(path):
    """
    Safely loads a JSON file. Returns empty dict if file is missing or invalid.
    """
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: 
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {path} contains invalid JSON. Returning empty dict.")
            return {}
    return {}

def normalize_key(s):
    """
    Creates a clean slug for URLs (e.g. "Premier League" -> "premierleague")
    """
    return re.sub(r'[^a-z0-9]', '', s.lower())

def build_menu_html(menu_items, section):
    """
    Generates HTML links for menus (Header, Hero, Footer).
    """
    html = ""
    for item in menu_items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        
        if section == 'header':
            style = ' style="color:#facc15; border-bottom:1px solid #facc15;"' if item.get('highlight') else ''
            html += f'<a href="{url}"{style}>{title}</a>'
            
        elif section == 'footer_leagues':
            icon = "🏆"
            t_low = title.lower()
            # Simple icon mapping based on league name
            if "soccer" in t_low or "premier" in t_low or "liga" in t_low: icon = "⚽"
            elif "nba" in t_low or "basket" in t_low: icon = "🏀"
            elif "nfl" in t_low or "football" in t_low: icon = "🏈"
            elif "mlb" in t_low or "baseball" in t_low: icon = "⚾"
            elif "ufc" in t_low or "boxing" in t_low: icon = "🥊"
            elif "f1" in t_low or "motor" in t_low: icon = "🏎️"
            elif "cricket" in t_low: icon = "🏏"
            elif "rugby" in t_low: icon = "🏉"
            elif "tennis" in t_low: icon = "🎾"
            elif "golf" in t_low: icon = "⛳"
            elif "hockey" in t_low or "nhl" in t_low: icon = "🏒"
            
            html += f'''
            <a href="{url}" class="league-card">
                <span class="l-icon">{icon}</span>
                <span>{title}</span>
            </a>'''
            
        elif section == 'hero':
            html += f'<a href="{url}" class="cat-pill">{title}</a>'
            
        elif section == 'footer_static':
             html += f'<a href="{url}" class="f-link">{title}</a>'
        
        else:
            html += f'<a href="{url}">{title}</a>'
            
    return html

# ==========================================
# 3. PAGE RENDERER
# ==========================================
def render_page(template, config, page_data):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    m = config.get('menus', {})
    
    html = template
    
    # --- 1. Basic Config & Theme Replacements ---
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    api_url = s.get('api_url', 'https://vercelapi-olive.vercel.app/api/sync-nodes')
    html = html.replace('{{API_URL}}', api_url)
    
    country = s.get('target_country', 'US')
    html = html.replace('{{TARGET_COUNTRY}}', country)
    
    lang_code = 'en-US' 
    if country == 'UK': lang_code = 'en-GB'
    html = html.replace('lang="en"', f'lang="{lang_code}"')
    
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    domain = s.get('domain', 'example.com')
    
    site_name = f"{p1}{p2}"
    html = html.replace('{{SITE_NAME}}', site_name)
    
    # --- Logo & OG Image ---
    raw_logo = s.get('logo_url', '')
    og_image = ""
    og_mime = "image/png"
    
    if raw_logo:
        if raw_logo.startswith('http'):
            og_image = raw_logo
        else:
            clean_domain = domain.rstrip('/')
            clean_logo = raw_logo.lstrip('/')
            og_image = f"https://{clean_domain}/{clean_logo}"
            
        low_img = og_image.lower()
        if low_img.endswith('.webp'): og_mime = "image/webp"
        elif low_img.endswith(('.jpg', '.jpeg')): og_mime = "image/jpeg"
        elif low_img.endswith('.gif'): og_mime = "image/gif"

    html = html.replace('{{OG_IMAGE}}', og_image)
    html = html.replace('{{OG_MIME}}', og_mime)

    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'): 
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img" alt="{site_name} Logo" fetchpriority="high"> {logo_html}'
        
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{DOMAIN}}', domain)
    html = html.replace('{{FAVICON}}', s.get('favicon_url', ''))

    # --- 2. Menus Injection ---
    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', []), 'header'))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), 'hero'))
    html = html.replace('{{FOOTER_STATIC}}', build_menu_html(m.get('footer_static', []), 'footer_static'))
    
    # Auto-generate footer league links based on priorities
    auto_footer_leagues = []
    priorities = config.get('sport_priorities', {}).get(country, {})
    if priorities:
        sorted_priorities = sorted(
            [item for item in priorities.items() if not item[0].startswith('_')],
            key=lambda item: item[1].get('score', 0),
            reverse=True
        )
        for name, data in sorted_priorities:
            if data.get('hasLink'):
                slug = normalize_key(name)
                auto_footer_leagues.append({'title': name, 'url': f'/{slug}-streams/'})
    html = html.replace('{{FOOTER_LEAGUES}}', build_menu_html(auto_footer_leagues, 'footer_leagues'))

    # --- 3. Footer Content ---
    html = html.replace('{{FOOTER_COPYRIGHT}}', s.get('footer_copyright', f"&copy; 2025 {domain}"))
    html = html.replace('{{FOOTER_DISCLAIMER}}', s.get('footer_disclaimer', ''))

    # --- 4. SEO & Metadata ---
    layout = page_data.get('layout', 'page')

    if layout == 'watch':
        html = html.replace('{{META_TITLE}}', '')
        html = html.replace('{{META_DESC}}', '')
        html = html.replace('<link rel="canonical" href="{{CANONICAL_URL}}">', '')
        html = html.replace('{{H1_TITLE}}', '')
        html = html.replace('{{HERO_TEXT}}', '')
    else:
        html = html.replace('{{META_TITLE}}', page_data.get('meta_title') or f"{site_name} - {page_data.get('title')}")
        html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
        html = html.replace('{{H1_TITLE}}', page_data.get('title', ''))
        html = html.replace('{{HERO_TEXT}}', page_data.get('hero_text') or page_data.get('meta_desc', ''))
        
        canon = page_data.get('canonical_url', '')
        if not canon and page_data.get('slug'):
            canon_slug = page_data.get('slug')
            canon = f"https://{domain}/{canon_slug}/" if canon_slug != 'home' else f"https://{domain}/"
        html = html.replace('{{CANONICAL_URL}}', canon)
    
    keywords = page_data.get('meta_keywords', '')
    if keywords: html = html.replace('{{META_KEYWORDS}}', f'<meta name="keywords" content="{keywords}">')
    else: html = html.replace('{{META_KEYWORDS}}', '')

    # --- 5. Layout Logic ---
    if layout == 'home':
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    elif '{{DISPLAY_HERO}}' in html:
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        # Hide live sections on non-home pages if template has them
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    html = html.replace('{{ARTICLE_CONTENT}}', page_data.get('content', ''))

    # --- 6. JS Injections (Dynamic Data) ---
    # Inject Priorities
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))
    
    # Inject Social Config
    social_data = config.get('social_sharing', {})
    excluded_list = [x.strip() for x in social_data.get('excluded_pages', '').split(',') if x.strip()]
    js_social_object = {"excluded": excluded_list, "counts": social_data.get('counts', {})}
    social_json = json.dumps(js_social_object)
    
    # Safe replacement for Social Config using regex
    if 'const SHARE_CONFIG' in html:
        html = re.sub(r'const SHARE_CONFIG = \{.*?\};', f'const SHARE_CONFIG = {social_json};', html, flags=re.DOTALL)

    # --- NEW: Inject League Map ---
    league_map_data = load_json(LEAGUE_MAP_PATH)
    html = html.replace('{{JS_LEAGUE_MAP}}', json.dumps(league_map_data))

    # --- NEW: Inject Image Map ---
    image_map_data = load_json(IMAGE_MAP_PATH)
    html = html.replace('{{JS_IMAGE_MAP}}', json.dumps(image_map_data))

    # --- 7. STATIC SCHEMA GENERATION ---
    schemas = []
    page_schemas = page_data.get('schemas', {})
    
    # Common IDs for Entity Stacking
    org_id = f"https://{domain}/#organization"
    website_id = f"https://{domain}/#website"
    
    # 1. Organization Schema (Enhanced)
    if page_schemas.get('org'):
        org_schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": org_id,
            "name": site_name,
            "url": f"https://{domain}/",
            "logo": {
                "@type": "ImageObject",
                "url": og_image, # This is your high-res logo from config
                "width": 512,    # Hardcoded assumption based on your input
                "height": 512,
                "caption": f"{site_name} Logo"
            }
        }
        schemas.append(org_schema)

    # 2. WebSite Schema
    if page_schemas.get('website'):
        website_schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": website_id,
            "url": f"https://{domain}/",
            "name": site_name,
            "publisher": {"@id": org_id}
        }
        schemas.append(website_schema)

    # 3. CollectionPage Schema (ONLY for Homepage)
    # This is the "Hub" definition that connects to the dynamic match list
    if page_data.get('slug') == 'home':
        collection_schema = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": f"https://{domain}/#webpage",
            "url": f"https://{domain}/",
            "name": page_data.get('meta_title') or f"{site_name} - Live Sports",
            "description": page_data.get('meta_desc', ''),
            "isPartOf": {"@id": website_id},
            "about": {"@id": org_id},
            "mainEntity": {"@id": f"https://{domain}/#matchlist"} # Links to the Dynamic JS List
        }
        schemas.append(collection_schema)

    # 4. FAQ Schema
    if page_schemas.get('faq'):
        valid_faqs = [
            {
                "@type": "Question", 
                "name": item.get('q'), 
                "acceptedAnswer": {"@type": "Answer", "text": item.get('a')}
            } 
            for item in page_schemas.get('faq_list', []) if item.get('q') and item.get('a')
        ]
        if valid_faqs:
            schemas.append({
                "@context": "https://schema.org", 
                "@type": "FAQPage", 
                "mainEntity": valid_faqs
            })

    # Wrap in separate script tags or one graph? 
    # For compatibility with your requested style, we'll output a single script with a graph.
    if schemas:
        # combine into one @graph for cleaner structure
        final_graph = {"@context": "https://schema.org", "@graph": schemas}
        # We strip the @context from individual items since it's at the root now
        for s in schemas:
            if "@context" in s: del s["@context"]
            
        schema_html = f'<script type="application/ld+json">{json.dumps(final_graph, indent=2)}</script>'
    else:
        schema_html = ''

    html = html.replace('{{SCHEMA_BLOCK}}', schema_html)
    
    preload_html = f'<link rel="preload" as="image" href="{s.get("logo_url")}" fetchpriority="high">' if s.get('logo_url') else ''
    html = html.replace('{{LOGO_PRELOAD}}', preload_html)

    return html

# ==========================================
# 4. MAIN BUILD PROCESS
# ==========================================
def build_site():
    print("--- 🔨 Starting Build Process ---")
    config = load_json(CONFIG_PATH)
    if not config: 
        print("❌ Config not found!")
        return

    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            master_template_content = f.read()
        print(f"✔️ Loaded Master Template: {TEMPLATE_PATH}")

        with open(WATCH_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            watch_template_content = f.read()
        print(f"✔️ Loaded Watch Template: {WATCH_TEMPLATE_PATH}")

    except FileNotFoundError as e:
        print(f"❌ Template file not found: {e.filename}")
        return

    print("📄 Building Pages...")
    for page in config.get('pages', []):
        slug = page.get('slug')
        if not slug:
            print(f"⚠️ Skipping page with no slug: {page.get('title')}")
            continue

        layout = page.get('layout')
        template_to_use = watch_template_content if layout == 'watch' else master_template_content
        print(f"   -> Building '{slug}' using {'WATCH' if layout == 'watch' else 'MASTER'} template")
        
        final_html = render_page(template_to_use, config, page)
        
        out_dir = os.path.join(OUTPUT_DIR, slug) if slug != 'home' else OUTPUT_DIR
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'index.html')
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

    print("✅ Build Complete.")

if __name__ == "__main__":
    build_site()
