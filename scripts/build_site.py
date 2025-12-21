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
    
    # 1. Menus
    header_html = ""
    for item in config.get('header_menu', []):
        header_html += f'<a href="{item["url"]}">{item["title"]}</a>'
    
    pills_html = ""
    for item in config.get('hero_categories', []):
        pills_html += f'<a href="{item["url"]}" class="cat-pill">{item["title"]}</a>'

    # 2. Template
    with open('assets/master_template.html', 'r', encoding='utf-8') as f: html = f.read()

    # 3. Injections
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    
    html = html.replace('{{META_TITLE}}', f"{p1}{p2} - #1 Free Live Sports")
    html = html.replace('{{META_DESC}}', s.get('custom_meta', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', 'example.com'))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    
    # Theme
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))

    # Logic
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'):
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
        
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{HEADER_MENU}}', header_html)
    html = html.replace('{{HERO_PILLS}}', pills_html)
    
    html = html.replace('{{H1_TITLE}}', f"{p1}{p2} - Live Sports")
    html = html.replace('{{HERO_TEXT}}', s.get('custom_meta', ''))
    
    if s.get('title_part_1'): html = html.replace('{{DISPLAY_HERO}}', 'block')
    else: html = html.replace('{{DISPLAY_HERO}}', 'none')

    # Content
    home_content = ""
    for p in config.get('pages', []):
        if p.get('slug') == 'home': home_content = p.get('content', '')
    html = html.replace('{{ARTICLE_CONTENT}}', home_content)

    # JS
    html = html.replace('{{GA_CODE}}', "")
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(config.get('sport_priorities', {})))

    with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
    print("✅ Build Complete")

if __name__ == "__main__":
    build_site()
