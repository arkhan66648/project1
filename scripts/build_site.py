import json
import os

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def build_site():
    print("--- 🔨 Building Site ---")
    config = load_json('data/config.json')
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    
    # 1. Prepare Menus
    header_html = ""
    for item in config.get('header_menu', []):
        header_html += f'<a href="{item["url"]}">{item["title"]}</a>'
    
    pills_html = ""
    for item in config.get('hero_categories', []):
        pills_html += f'<a href="{item["url"]}" class="cat-pill">{item["title"]}</a>'

    # 2. Read Template
    with open('assets/master_template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    # 3. Base Replacements (Config Data)
    template = template.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    template = template.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    template = template.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    template = template.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    template = template.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    template = template.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    
    # Target Country (Critical for Backend Fetch)
    template = template.replace('{{TARGET_COUNTRY}}', s.get('target_country', 'US'))

    # Logo Logic
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'):
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
    template = template.replace('{{LOGO_HTML}}', logo_html)

    # 4. Generate Index.html (Home)
    home_page = next((p for p in config.get('pages', []) if p['slug'] == 'home'), None)
    
    html = template
    html = html.replace('{{META_TITLE}}', f"{p1}{p2} - Live Sports")
    html = html.replace('{{META_DESC}}', s.get('custom_meta', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    html = html.replace('{{HEADER_MENU}}', header_html)
    html = html.replace('{{HERO_PILLS}}', pills_html)
    html = html.replace('{{H1_TITLE}}', f"{p1} - {p2}")
    html = html.replace('{{HERO_TEXT}}', s.get('custom_meta', ''))
    
    if s.get('title_part_1'): html = html.replace('{{DISPLAY_HERO}}', 'block')
    else: html = html.replace('{{DISPLAY_HERO}}', 'none')

    # Content & Schemas
    if home_page:
        html = html.replace('{{ARTICLE_CONTENT}}', home_page.get('content', ''))
    else:
        html = html.replace('{{ARTICLE_CONTENT}}', '')

    # Backend sends schema in the JSON response as `seo.live_broadcast` and `seo.upcoming_list`
    # The Frontend JS puts it into the <script id="dynamic-schema"> tag.
    # So we leave {{SCHEMA_BLOCK}} empty here, OR if you have Static Schemas (like Organization), put them here.
    # For now, we rely on the Backend+JS for the dynamic match schemas.
    html = html.replace('{{SCHEMA_BLOCK}}', '') 
    
    # Clean up unused placeholders
    html = html.replace('{{GA_CODE}}', '')
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(config.get('sport_priorities', {})))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("✅ Build Complete")

if __name__ == "__main__":
    build_site()
