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

def build_menu_html(menu_items, is_pill=False, is_footer=False):
    html = ""
    for item in menu_items:
        cls = 'class="cat-pill"' if is_pill else ''
        if is_footer: cls = 'class="footer-link"'
        html += f'<a href="{item["url"]}" {cls}>{item["title"]}</a>'
    return html

def generate_entity_footer(entities):
    if not entities: return ""
    html = '<div class="entity-footer-section"><h3>Trending Searches</h3><div class="entity-tags">'
    for item in entities:
        safe_kw = item['keyword'].replace('"', '&quot;')
        html += f'<button class="entity-tag" onclick="triggerEntityPopup(\'{safe_kw}\')">{safe_kw}</button>'
    html += '</div></div>'
    return html

def render_page(template, config, page_data):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    m = config.get('menus', {})
    
    html = template
    # Basic Config
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    html = html.replace('{{TARGET_COUNTRY}}', s.get('target_country', 'US'))
    
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    domain = s.get('domain', 'example.com')
    
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'): logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{DOMAIN}}', domain)
    html = html.replace('{{FAVICON}}', s.get('favicon_url', ''))

    # Menus
    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', [])))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), True))
    
    # Footer Injection
    html = html.replace('{{FOOTER_LEAGUES}}', build_menu_html(m.get('footer_leagues', []), is_footer=True))
    html = html.replace('{{FOOTER_STATIC}}', build_menu_html(m.get('footer_static', []), is_footer=True))
    html = html.replace('{{FOOTER_COPYRIGHT}}', s.get('footer_copyright', f"&copy; 2025 {domain}"))
    
    disclaimer = s.get('footer_disclaimer', '')
    if disclaimer: html = html.replace('{{FOOTER_DISCLAIMER}}', f'<div class="disclaimer">{disclaimer}</div>')
    else: html = html.replace('{{FOOTER_DISCLAIMER}}', '')

    html = html.replace('{{ENTITY_SECTION}}', generate_entity_footer(config.get('entity_stacking', [])))
    
    # SEO
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

    # Layout
    layout = page_data.get('layout', 'page')
    if layout == 'home':
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    else:
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    html = html.replace('{{ARTICLE_CONTENT}}', page_data.get('content', ''))

    # Priorities (Always Inject for Home)
    target_c = s.get('target_country', 'US')
    priorities = config.get('sport_priorities', {}).get(target_c, {})
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))

    # Schemas (Static Org only here)
    schemas = []
    if page_data.get('schemas', {}).get('org'):
        schemas.append({
            "@context": "https://schema.org", "@type": "Organization",
            "name": f"{p1}{p2}", "url": f"https://{domain}", "logo": s.get('logo_url')
        })
    
    if schemas: html = html.replace('{{SCHEMA_BLOCK}}', f'<script type="application/ld+json">{json.dumps(schemas)}</script>')
    else: html = html.replace('{{SCHEMA_BLOCK}}', '')

    return html

def build_site():
    print("--- 🔨 Starting Build Process ---")
    config = load_json(CONFIG_PATH)
    if not config: return

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    print("📄 Building Pages...")
    for page in config.get('pages', []):
        slug = page.get('slug')
        final_html = render_page(template, config, page)
        
        if slug == 'home':
            out_path = os.path.join(OUTPUT_DIR, 'index.html')
        else:
            dir_path = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(dir_path, exist_ok=True)
            out_path = os.path.join(dir_path, 'index.html')
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

    print("✅ Build Complete (Auto-Generation Stopped)")

if __name__ == "__main__":
    build_site()
