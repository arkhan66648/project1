import json
import os
import re

# ==========================================
# 1. CONFIGURATION
# ==========================================
CONFIG_PATH = 'data/config.json'
LEAGUE_MAP_PATH = 'assets/data/league_map.json' 
IMAGE_MAP_PATH = 'assets/data/image_map.json'
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

def ensure_unit(val, unit='px'):
    """
    Ensures a value has a CSS unit. e.g. "6" -> "6px", "100%" -> "100%".
    """
    s_val = str(val).strip()
    if not s_val: return f"0{unit}"
    if s_val.isdigit(): return f"{s_val}{unit}"
    return s_val

def build_menu_html(menu_items, section):
    """
    Generates HTML links for menus (Header, Hero, Footer).
    """
    html = ""
    for item in menu_items:
        title = item.get('title', 'Link')
        url = item.get('url', '#')
        
        if section == 'header':
            style = ' style="color:var(--accent-gold); border-bottom:1px solid var(--accent-gold);"' if item.get('highlight') else ''
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
    
    # --- 1. THEME ENGINE INJECTION ---
    # Define Defaults to prevent build crashes
    defaults = {
        # Core Colors & Base
        'brand_primary': '#D00000', 'brand_dark': '#8a0000', 'accent_gold': '#FFD700', 'status_green': '#22c55e',
        'bg_body': '#050505', 'bg_panel': '#1e293b', 'bg_glass': 'rgba(30, 41, 59, 0.7)',
        'text_main': '#f1f5f9', 'text_muted': '#94a3b8', 'border_color': '#334155', 'scrollbar_thumb_color': '#475569',
        'font_family_base': 'system-ui, -apple-system, sans-serif', 'font_family_headings': 'inherit',
        'base_font_size': '14px', 'base_line_height': '1.5', 
        'container_max_width': '1100px', 'border_radius_base': '6px', 'button_border_radius': '4px',
        'card_shadow': '0 4px 6px -1px rgba(0,0,0,0.1)',
        
        # Global Layout & Animation
        'layout_mode': '', 'page_bg_anim': '',
        
        # Header Layout
        'header_bg': 'rgba(5, 5, 5, 0.8)', 'header_text_color': '#f1f5f9', 'header_link_active_color': '#D00000',
        'header_border_bottom': '1px solid #334155', 'logo_p1_color': '#f1f5f9', 'logo_p2_color': '#D00000',
        'logo_image_size': '40px',
        'header_logo_order': '1', 'header_nav_order': '2', 'header_justify': 'space-between',
        'header_sticky_class': '',
        
        # Hero Section
        'hero_bg_style': 'solid', 'hero_bg_solid': '#1a0505', 
        'hero_h1_color': '#ffffff', 'hero_intro_color': '#94a3b8',
        'hero_pill_bg': 'rgba(255,255,255,0.05)', 'hero_pill_text': '#f1f5f9', 'hero_pill_border': 'rgba(255,255,255,0.1)',
        'hero_pill_hover_bg': '#D00000', 'hero_pill_hover_text': '#ffffff', 'hero_pill_hover_border': '#D00000',
        'hero_text_align': 'center', 'hero_animation_class': '', 'display_hero': 'block',

        # Featured Match
        'display_featured': 'block', 'featured_bg': '#1e293b', 'featured_border': '1px solid #334155',

        # Match List
        'match_row_bg': '#1e293b', 'match_row_border': '#334155', 
        'match_row_live_border_left': '4px solid #22c55e', 
        'match_row_live_bg_start': 'rgba(34, 197, 94, 0.1)', 'match_row_live_bg_end': 'transparent',
        'match_row_hover_border': '#D00000', 'match_row_hover_transform': 'translateY(-2px)',
        'match_row_hover_bg': '#1e293b',
        'match_row_time_main_color': '#f1f5f9', 'match_row_time_sub_color': '#94a3b8',
        'match_row_live_text_color': '#22c55e', 'match_row_league_tag_color': '#94a3b8', 'match_row_team_name_color': '#f1f5f9',
        'match_row_btn_watch_bg': '#D00000', 'match_row_btn_watch_text': '#ffffff', 
        'match_row_btn_watch_hover_bg': '#b91c1c', 'match_row_btn_watch_hover_transform': 'scale(1.05)',
        'match_row_hd_badge_bg': 'rgba(0,0,0,0.3)', 'match_row_hd_badge_border': 'rgba(255,255,255,0.2)', 'match_row_hd_badge_text': '#facc15',
        'match_row_btn_notify_bg': 'transparent', 'match_row_btn_notify_border': '#334155', 'match_row_btn_notify_text': '#94a3b8',
        'match_row_btn_notify_active_bg': '#22c55e', 'match_row_btn_notify_active_border': '#22c55e', 'match_row_btn_notify_active_text': '#ffffff',
        'match_row_btn_copy_link_color': '#64748b', 'match_row_btn_copy_link_hover_color': '#D00000',
        'match_row_layout_class': 'layout-standard', 'live_animation_class': '',

        # Footer
        'footer_bg_start': '#0f172a', 'footer_bg_end': '#020617', 'footer_border_top': '1px solid #334155',
        'footer_heading_color': '#94a3b8', 'footer_link_color': '#64748b', 'footer_link_hover_color': '#f1f5f9',
        'footer_link_hover_transform': 'translateX(5px)', 'footer_copyright_color': '#475569', 'footer_desc_color': '#64748b',
        'footer_animation_class': '', 'footer_bg_css': '#0f172a', 'footer_align': 'left',

        # Socials
        'social_sidebar_bg': 'rgba(15, 23, 42, 0.8)', 'social_sidebar_border': '#334155', 'social_sidebar_shadow': '0 4px 10px rgba(0,0,0,0.3)',
        'social_btn_bg': 'rgba(30, 41, 59, 0.8)', 'social_btn_border': '#334155', 'social_btn_color': '#94a3b8',
        'social_btn_hover_bg': '#1e293b', 'social_btn_hover_border': '#D00000', 'social_btn_hover_transform': 'translateX(5px)',
        'social_count_color': '#64748b',
        'mobile_footer_bg': 'rgba(5, 5, 5, 0.9)', 'mobile_footer_border_top': '1px solid #334155', 'mobile_footer_shadow': '0 -4px 10px rgba(0,0,0,0.5)',
        'social_desktop_top': '50%', 'social_desktop_left': '0', 'social_desktop_scale': '1.0',
        'mobile_footer_height': '60px',

        # Utility & Text
        'copy_toast_bg': '#22c55e', 'copy_toast_text': '#ffffff', 'copy_toast_border': '#16a34a',
        'back_to_top_bg': '#D00000', 'back_to_top_icon_color': '#ffffff', 'back_to_top_shadow': '0 4px 10px rgba(208,0,0,0.4)',
        'back_to_top_radius': '50%', 'back_to_top_size': '40px',
        'sys_status_dot_color': '#22c55e', 'sys_status_bg': 'rgba(34, 197, 94, 0.1)', 'sys_status_border': 'rgba(34, 197, 94, 0.2)', 'sys_status_text': '#22c55e',
        'skeleton_gradient_start': '#1e293b', 'skeleton_gradient_mid': '#334155', 'skeleton_gradient_end': '#1e293b',
        'skeleton_border_color': '#334155',
        'section_logo_size': '24px',
        'show_more_btn_bg': '#1e293b', 'show_more_btn_border': '#334155', 'show_more_btn_text': '#94a3b8',
        'show_more_btn_hover_bg': '#D00000', 'show_more_btn_hover_border': '#D00000', 'show_more_btn_hover_text': '#ffffff',
        'show_more_btn_radius': '30px',
        'league_card_bg': 'rgba(30, 41, 59, 0.5)', 'league_card_border': '#334155', 'league_card_text': '#f1f5f9',
        'league_card_hover_bg': '#1e293b', 'league_card_hover_border': '#D00000',
        'footer_brand_color': '#ffffff', 'mobile_footer_btn_active_bg': 'rgba(255,255,255,0.1)',
        'social_telegram_color': '#0088cc', 'social_whatsapp_color': '#25D366', 'social_reddit_color': '#FF4500', 'social_twitter_color': '#1DA1F2',
        'social_btn_hover_shadow_color': 'rgba(0,0,0,0.3)',
        'footer_grid_columns': '1fr 1fr', 'footer_text_align_mobile': 'left',
        'footer_grid_columns_desktop': '1fr 1fr 1fr', 'footer_text_align_desktop': 'left', 'footer_last_col_align_desktop': 'right',
        
        # Dynamic Text Placeholders
        'text_wildcard_title': '', 'text_top_upcoming_title': '',
        'text_live_section_title': 'Trending Live', 'text_show_more': 'Show More Matches',
        'text_watch_btn': 'WATCH', 'text_hd_badge': 'HD',
        'text_section_link': 'View All', 'text_section_prefix': 'Upcoming',
        'wildcard_category': ''
    }

    # Merge Config with Defaults
    theme = {}
    for k, v in defaults.items():
        val = t.get(k)
        # Apply px units to specific number fields
        if k in ['border_radius_base', 'container_max_width', 'base_font_size', 'logo_image_size', 'button_border_radius', 
                 'show_more_btn_radius', 'back_to_top_size', 'section_logo_size']:
            if val: val = ensure_unit(val, 'px')
        
        theme[k] = val if val else v

    # Inject into HTML (Loop for standard variables)
    for key, val in theme.items():
        placeholder = f"{{{{THEME_{key.upper()}}}}}"
        html = html.replace(placeholder, str(val))

    # --- 2. CLASS & LOGIC INJECTIONS ---
    
    # 2a. Global Layout & Page Animation
    # Combine layout mode + page background animation class
    layout_cls = f"{theme.get('layout_mode', '')} {theme.get('page_bg_anim', '')}".strip()
    html = html.replace('{{THEME_LAYOUT_MODE}}', layout_cls)
    
    # 2b. Section Animations & Classes
    html = html.replace('{{HEADER_STICKY_CLASS}}', theme.get('header_sticky_class', ''))
    html = html.replace('{{HERO_ANIMATION_CLASS}}', theme.get('hero_animation_class', ''))
    html = html.replace('{{LIVE_ANIMATION_CLASS}}', theme.get('live_animation_class', ''))
    html = html.replace('{{FOOTER_ANIMATION_CLASS}}', theme.get('footer_animation_class', ''))

    # 2c. Hero Background Logic (Complex CSS)
    hero_style = theme.get('hero_bg_style', 'solid')
    hero_css = ""
    if hero_style == 'gradient':
        start = theme.get('hero_gradient_start', '#1a0505')
        end = theme.get('hero_gradient_end', '#000000')
        hero_css = f"background: linear-gradient(135deg, {start} 0%, {end} 100%);"
    elif hero_style == 'image':
        img = theme.get('hero_bg_image_url', '')
        op = theme.get('hero_bg_image_overlay_opacity', '0.7')
        hero_css = f"background: linear-gradient(rgba(0,0,0,{op}), rgba(0,0,0,{op})), url('{img}'); background-size: cover; background-position: center;"
    else:
        solid = theme.get('hero_bg_solid', '#1a0505')
        hero_css = f"background: {solid};"
    html = html.replace('{{HERO_BG_CSS}}', hero_css)
    
    # 2d. Inject Full Theme Config for JS access
    html = html.replace('{{JS_THEME_CONFIG}}', json.dumps(theme))
    
    # 2e. Wildcard & Text
    wildcard_cat = theme.get('wildcard_category', '')
    html = html.replace('{{WILDCARD_CATEGORY}}', wildcard_cat)
    
    html = html.replace('{{TEXT_LIVE_SECTION_TITLE}}', theme.get('text_live_section_title', 'Trending Live'))
    html = html.replace('{{TEXT_SHOW_MORE}}', theme.get('text_show_more', 'Show More Matches'))
    html = html.replace('{{TEXT_WATCH_BTN}}', theme.get('text_watch_btn', 'WATCH'))
    html = html.replace('{{TEXT_HD_BADGE}}', theme.get('text_hd_badge', 'HD'))
    html = html.replace('{{TEXT_SECTION_LINK}}', theme.get('text_section_link', 'View All'))
    html = html.replace('{{TEXT_SECTION_PREFIX}}', theme.get('text_section_prefix', 'Upcoming'))
    html = html.replace('{{TEXT_WILDCARD_TITLE}}', theme.get('text_wildcard_title', ''))
    html = html.replace('{{TEXT_TOP_UPCOMING_TITLE}}', theme.get('text_top_upcoming_title', ''))

    # --- 3. BASIC CONFIG REPLACEMENTS (Legacy/Core) ---
    html = html.replace('{{BRAND_PRIMARY}}', theme.get('brand_primary'))
    
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

    # --- 4. Menus Injection ---
    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', []), 'header'))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), 'hero'))
    html = html.replace('{{FOOTER_STATIC}}', build_menu_html(m.get('footer_static', []), 'footer_static'))
    
    # Auto-generate footer league links
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

    # --- 5. Footer Content ---
    html = html.replace('{{FOOTER_COPYRIGHT}}', s.get('footer_copyright', f"&copy; 2025 {domain}"))
    html = html.replace('{{FOOTER_DISCLAIMER}}', s.get('footer_disclaimer', ''))

    # --- 6. SEO & Metadata ---
    layout = page_data.get('layout', 'page')

    if layout == 'watch':
        html = html.replace('{{META_TITLE}}', '')
        html = html.replace('{{META_DESC}}', '')
        html = html.replace('<link rel="canonical" href="{{CANONICAL_URL}}">', '')
        html = html.replace('{{H1_TITLE}}', '')
        html = html.replace('{{HERO_TEXT}}', '')
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        html = html.replace('</head>', '<style>.hero, #live-section, #upcoming-container { display: none !important; }</style></head>')
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

    # --- 7. Layout Logic (Home vs Page) ---
    if layout == 'home':
        display_val = theme.get('display_hero', 'block')
        html = html.replace('{{DISPLAY_HERO}}', display_val)
    elif layout != 'watch': 
        if '{{DISPLAY_HERO}}' in html:
            html = html.replace('{{DISPLAY_HERO}}', 'none')
            html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    html = html.replace('{{ARTICLE_CONTENT}}', page_data.get('content', ''))

    # --- 8. JS Injections (Dynamic Data) ---
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))
    
    social_data = config.get('social_sharing', {})
    excluded_list = [x.strip() for x in social_data.get('excluded_pages', '').split(',') if x.strip()]
    js_social_object = {"excluded": excluded_list, "counts": social_data.get('counts', {})}
    social_json = json.dumps(js_social_object)
    
    if 'const SHARE_CONFIG' in html:
        html = re.sub(r'const SHARE_CONFIG = \{.*?\};', f'const SHARE_CONFIG = {social_json};', html, flags=re.DOTALL)

    league_map_data = load_json(LEAGUE_MAP_PATH)
    html = html.replace('{{JS_LEAGUE_MAP}}', json.dumps(league_map_data))

    image_map_data = load_json(IMAGE_MAP_PATH)
    html = html.replace('{{JS_IMAGE_MAP}}', json.dumps(image_map_data))

    # --- 9. STATIC SCHEMA GENERATION ---
    schemas = []
    page_schemas = page_data.get('schemas', {})
    org_id = f"https://{domain}/#organization"
    website_id = f"https://{domain}/#website"
    
    if page_schemas.get('org'):
        org_schema = {
            "@context": "https://schema.org", "@type": "Organization", "@id": org_id, "name": site_name, "url": f"https://{domain}/",
            "logo": { "@type": "ImageObject", "url": og_image, "width": 512, "height": 512, "caption": f"{site_name} Logo" }
        }
        schemas.append(org_schema)

    if page_schemas.get('website'):
        website_schema = {
            "@context": "https://schema.org", "@type": "WebSite", "@id": website_id, "url": f"https://{domain}/",
            "name": site_name, "publisher": {"@id": org_id}
        }
        schemas.append(website_schema)

    if page_data.get('slug') == 'home':
        collection_schema = {
            "@context": "https://schema.org", "@type": "CollectionPage", "@id": f"https://{domain}/#webpage",
            "url": f"https://{domain}/", "name": page_data.get('meta_title') or f"{site_name} - Live Sports",
            "description": page_data.get('meta_desc', ''), "isPartOf": {"@id": website_id}, "about": {"@id": org_id},
            "mainEntity": {"@id": f"https://{domain}/#matchlist"} 
        }
        schemas.append(collection_schema)

    if page_schemas.get('faq'):
        valid_faqs = [{ "@type": "Question", "name": item.get('q'), "acceptedAnswer": {"@type": "Answer", "text": item.get('a')} } 
            for item in page_schemas.get('faq_list', []) if item.get('q') and item.get('a')]
        if valid_faqs:
            schemas.append({ "@context": "https://schema.org", "@type": "FAQPage", "mainEntity": valid_faqs })

    if schemas:
        final_graph = {"@context": "https://schema.org", "@graph": schemas}
        for s in schemas:
            if "@context" in s: del s["@context"]
        schema_html = f'<script type="application/ld+json">{json.dumps(final_graph, indent=2)}</script>'
    else:
        schema_html = ''

    html = html.replace('{{SCHEMA_BLOCK}}', schema_html)
    
    preload_html = f'<link rel="preload" as="image" href="{s.get("logo_url")}" fetchpriority="high">' if s.get('logo_url') else ''
    html = html.replace('{{LOGO_PRELOAD}}', preload_html)
    
    html = html.replace('{{HEADER_CLASSES}}', '')
    html = html.replace('{{MAIN_CONTAINER_CLASSES}}', '')
    html = html.replace('{{FOOTER_CLASSES}}', '')

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
