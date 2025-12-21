import json
import os
import shutil
import re

CONFIG_PATH = 'data/config.json'
TEMPLATE_PATH = 'assets/master_template.html'
OUTPUT_DIR = '.' 

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def build_menu_html(menu_items, is_pill=False):
    html = ""
    for item in menu_items:
        cls = 'class="cat-pill"' if is_pill else ''
        html += f'<a href="{item["url"]}" {cls}>{item["title"]}</a>'
    return html

def generate_entity_stacking(entities):
    if not entities: return ""
    html = '<div class="entity-bar" style="margin-top:20px; text-align:center;">'
    html += '<span style="color:#666; font-size:0.8rem; margin-right:10px;">Trending:</span>'
    js_data = []
    for idx, item in enumerate(entities):
        safe_kw = item['keyword'].replace('"', '&quot;')
        html += f'<button onclick="openEntityPopup({idx})" style="background:none; color:#888; border:1px solid #333; border-radius:4px; padding:4px 10px; font-size:0.75rem; margin:0 4px;">{safe_kw}</button>'
        js_data.append(item['content'])
    html += '</div>'
    js_script = f"""
    <script>
        const ENTITY_DATA = {json.dumps(js_data)};
        function openEntityPopup(idx) {{
            const content = ENTITY_DATA[idx];
            const modal = document.createElement('div');
            modal.style.cssText = "position:fixed; inset:0; background:rgba(0,0,0,0.9); z-index:9999; display:flex; justify-content:center; align-items:center; padding:20px;";
            modal.innerHTML = `<div style="background:#111; border:1px solid #444; padding:30px; border-radius:8px; max-width:500px; width:100%; color:#fff; position:relative;">
                <button onclick="this.closest('div').parentElement.remove()" style="position:absolute; top:10px; right:10px; background:none; color:#fff; font-size:20px;">&times;</button>
                ${{content}}
                <div style="margin-top:20px; text-align:center;"><a href="/" style="background:#D00000; color:#fff; padding:10px 20px; border-radius:4px; text-decoration:none; font-weight:bold;">Go to Homepage</a></div>
            </div>`;
            document.body.appendChild(modal);
        }}
    </script>
    """
    return html + js_script

def render_page(template, config, page_data, is_league_page=False, league_filter=None):
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    m = config.get('menus', {})
    
    html = template
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
    if s.get('logo_url'):
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
    
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{DOMAIN}}', domain)
    html = html.replace('{{FAVICON}}', s.get('logo_url', ''))

    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', [])))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), True))
    
    entity_html = generate_entity_stacking(config.get('entity_stacking', []))
    
    html = html.replace('{{META_TITLE}}', page_data.get('meta_title') or f"{p1}{p2} - {page_data.get('title')}")
    html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
    html = html.replace('{{H1_TITLE}}', page_data.get('title', ''))
    html = html.replace('{{HERO_TEXT}}', page_data.get('hero_text') or page_data.get('meta_desc', ''))

    layout = page_data.get('layout', 'page')
    if layout == 'home' or is_league_page:
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    else:
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    content = page_data.get('content', '')
    if entity_html: content += entity_html
    html = html.replace('{{ARTICLE_CONTENT}}', content)

    target_c = s.get('target_country', 'US')
    priorities = config.get('sport_priorities', {}).get(target_c, {})
    
    if is_league_page and league_filter:
        prio_data = priorities.get(league_filter, {})
        is_league_type = prio_data.get('isLeague', False)
        page_priorities = { league_filter: prio_data }
        html = html.replace('{{JS_PRIORITIES}}', json.dumps(page_priorities))
        filter_script = f"""
        <script>
            window.addEventListener('DOMContentLoaded', () => {{
                const liveSec = document.getElementById('live-section');
                if(liveSec) liveSec.style.display = 'none';
            }});
        </script>
        """
        html = html.replace('</body>', filter_script + '</body>')
    else:
        html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))

    schemas = []
    if page_data.get('schemas', {}).get('org'):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": f"{p1}{p2}",
            "url": f"https://{domain}",
            "logo": s.get('logo_url')
        })
    
    if schemas:
        schema_script = f'<script type="application/ld+json">{json.dumps(schemas)}</script>'
        html = html.replace('{{SCHEMA_BLOCK}}', schema_script)
    else:
        html = html.replace('{{SCHEMA_BLOCK}}', '')

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

    print("🏆 Building League Pages...")
    country = config.get('site_settings', {}).get('target_country', 'US')
    priorities = config.get('sport_priorities', {}).get(country, {})
    
    for name, data in priorities.items():
        if isinstance(data, int): data = {'score': data, 'isLeague': False, 'hasLink': False}
        
        if data.get('hasLink'):
            print(f"   - Generating League Page: {name}")
            slug = slugify(name)
            page_data = {
                'title': f"{name} Live Streams",
                'meta_title': f"Watch {name} Live Free - {config['site_settings'].get('domain')}",
                'meta_desc': f"The best source for {name} live streams. Watch high quality {name} matches free.",
                'layout': 'league', 
                'content': f"<h2>{name} Schedule</h2><p>Check below for the latest upcoming {name} matches.</p>",
                'schemas': {'org': True}
            }
            final_html = render_page(template, config, page_data, is_league_page=True, league_filter=name)
            
            # FIXED: Page is now at root (e.g. /nba/index.html) instead of /league/nba/
            dir_path = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(final_html)

    print("✅ Build Complete!")

if __name__ == "__main__":
    build_site()
