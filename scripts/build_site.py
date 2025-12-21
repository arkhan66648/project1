import json
import os

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def build_site():
    print("--- 🔨 Building Static Site ---")
    
    # 1. Load Data
    config = load_json('data/config.json')
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    
    # 2. Generate Menus
    header_html = ""
    for item in config.get('header_menu', []):
        header_html += f'<a href="{item["url"]}">{item["title"]}</a>'
        
    pills_html = ""
    for item in config.get('hero_categories', []):
        pills_html += f'<a href="{item["url"]}" class="cat-pill">{item["title"]}</a>'

    # 3. Read Template
    if not os.path.exists('assets/master_template.html'):
        print("Error: assets/master_template.html not found")
        return

    with open('assets/master_template.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 4. Inject Static Data
    # Colors & Fonts
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#0f0f0f'))
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#00e5ff'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#00b2cc'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    
    # Meta
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'Hub')
    html = html.replace('{{META_TITLE}}', f"{p1}{p2} - #1 Free Live Sports")
    html = html.replace('{{META_DESC}}', s.get('custom_meta', ''))
    html = html.replace('{{DOMAIN}}', s.get('domain', ''))
    html = html.replace('{{FAVICON}}', s.get('favicon', ''))
    html = html.replace('{{LOGO_URL}}', s.get('logo_url', ''))
    
    # GA
    ga_id = s.get('ga_id', '')
    if ga_id:
        ga_code = f"<script async src='https://www.googletagmanager.com/gtag/js?id={ga_id}'></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{ga_id}');</script>"
    else:
        ga_code = ""
    html = html.replace('{{GA_CODE}}', ga_code)
    
    # UI Elements
    c1 = t.get('title_color_1', '#ffffff')
    c2 = t.get('title_color_2', '#00e5ff')
    logo_ui = f'<div class="logo-text" style="color:{c1}">{p1}<span style="color:{c2}">{p2}</span></div>'
    if s.get('logo_url'):
        logo_ui = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_ui}'
    
    html = html.replace('{{LOGO_HTML}}', logo_ui)
    html = html.replace('{{HEADER_MENU}}', header_html)
    html = html.replace('{{HERO_PILLS}}', pills_html)
    
    html = html.replace('{{H1_TITLE}}', f"{p1}{p2} - Live Sports")
    html = html.replace('{{HERO_TEXT}}', s.get('custom_meta', ''))

    if s.get('title_part_1'):
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    else:
        html = html.replace('{{DISPLAY_HERO}}', 'none')

    # Priorities (For JS)
    html = html.replace('{{JS_PRIORITIES}}', json.dumps(config.get('sport_priorities', {})))
    
    # Content (Home)
    home_content = ""
    for p in config.get('pages', []):
        if p.get('slug') == 'home': home_content = p.get('content', '')
    html = html.replace('{{ARTICLE_CONTENT}}', home_content)

    # 5. Write Output
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ index.html rebuilt successfully.")

if __name__ == "__main__":
    build_site()
