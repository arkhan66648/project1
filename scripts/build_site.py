import json
import os
import shutil
import re

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG_PATH = 'data/config.json'
TEMPLATE_PATH = 'assets/master_template.html'
OUTPUT_DIR = '.' # Root directory for GitHub Pages

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
    """Generates the hidden popups and the script to trigger them."""
    if not entities: return ""
    
    # 1. Generate the Menu Items (Keywords)
    html = '<div class="entity-bar" style="margin-top:20px; text-align:center;">'
    html += '<span style="color:#666; font-size:0.8rem; margin-right:10px;">Trending:</span>'
    
    js_data = []
    
    for idx, item in enumerate(entities):
        safe_kw = item['keyword'].replace('"', '&quot;')
        html += f'<button onclick="openEntityPopup({idx})" style="background:none; color:#888; border:1px solid #333; border-radius:4px; padding:4px 10px; font-size:0.75rem; margin:0 4px;">{safe_kw}</button>'
        js_data.append(item['content'])
        
    html += '</div>'

    # 2. Inject the JS Logic
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
    """Core function to replace placeholders in the master template."""
    s = config.get('site_settings', {})
    t = config.get('theme', {})
    m = config.get('menus', {})
    
    # 1. Basic Replacements
    html = template
    html = html.replace('{{BRAND_PRIMARY}}', t.get('brand_primary', '#D00000'))
    html = html.replace('{{BRAND_DARK}}', t.get('brand_dark', '#8a0000'))
    html = html.replace('{{ACCENT_GOLD}}', t.get('accent_gold', '#FFD700'))
    html = html.replace('{{BG_BODY}}', t.get('bg_body', '#050505'))
    html = html.replace('{{HERO_GRADIENT}}', t.get('hero_gradient_start', '#1a0505'))
    html = html.replace('{{FONT_FAMILY}}', t.get('font_family', 'system-ui'))
    html = html.replace('{{TARGET_COUNTRY}}', s.get('target_country', 'US'))
    
    # 2. Site Identity
    p1 = s.get('title_part_1', 'Stream')
    p2 = s.get('title_part_2', 'East')
    domain = s.get('domain', 'example.com')
    
    logo_html = f'<div class="logo-text">{p1}<span>{p2}</span></div>'
    if s.get('logo_url'):
        logo_html = f'<img src="{s.get("logo_url")}" class="logo-img"> {logo_html}'
    
    html = html.replace('{{LOGO_HTML}}', logo_html)
    html = html.replace('{{DOMAIN}}', domain)
    html = html.replace('{{FAVICON}}', s.get('logo_url', '')) # Use logo as favicon fallback

    # 3. Menus
    html = html.replace('{{HEADER_MENU}}', build_menu_html(m.get('header', [])))
    html = html.replace('{{HERO_PILLS}}', build_menu_html(m.get('hero', []), True))
    
    # Footer construction (not in template placeholders, so we append to Article Content or hardcode structure)
    # NOTE: The Step 1 template had a simple footer. We will update the footer dynamically here
    # by replacing the generic footer HTML if we want, or just accept the template footer.
    # We will inject the entity stacking bar BEFORE the footer.
    entity_html = generate_entity_stacking(config.get('entity_stacking', []))
    
    # 4. Page Specific Data
    html = html.replace('{{META_TITLE}}', page_data.get('meta_title') or f"{p1}{p2} - {page_data.get('title')}")
    html = html.replace('{{META_DESC}}', page_data.get('meta_desc', ''))
    html = html.replace('{{H1_TITLE}}', page_data.get('title', ''))
    
    # Hero Text (Use custom hero text if available, else meta desc)
    html = html.replace('{{HERO_TEXT}}', page_data.get('hero_text') or page_data.get('meta_desc', ''))

    # Layout Logic
    layout = page_data.get('layout', 'page')
    
    if layout == 'home' or is_league_page:
        html = html.replace('{{DISPLAY_HERO}}', 'block')
    else:
        html = html.replace('{{DISPLAY_HERO}}', 'none')
        # If standard page, hide the match container divs via CSS injection
        html = html.replace('</head>', '<style>#live-section, #upcoming-container { display: none !important; }</style></head>')

    # Content
    content = page_data.get('content', '')
    if entity_html: content += entity_html # Append entity bar
    html = html.replace('{{ARTICLE_CONTENT}}', content)

    # 5. PRIORITIES & JS INJECTION
    target_c = s.get('target_country', 'US')
    priorities = config.get('sport_priorities', {}).get(target_c, {})
    
    if is_league_page and league_filter:
        # LEAGUE PAGE MAGIC:
        # 1. We inject a JS snippet that forces the frontend to filter by this league.
        # 2. We Pass a modified Priorities object that ONLY has this league (so the sorter groups it alone).
        
        # Determine if we filter by League Name or Sport Name based on config
        prio_data = priorities.get(league_filter, {})
        is_league_type = prio_data.get('isLeague', False)
        
        # Override Priorities for this page
        page_priorities = { league_filter: prio_data }
        html = html.replace('{{JS_PRIORITIES}}', json.dumps(page_priorities))
        
        # Inject Filter Script
        # This script runs after DOMContentLoaded and monkey-patches the data or hides elements
        filter_script = f"""
        <script>
            // INJECTED BY BUILDER FOR LEAGUE PAGE
            window.addEventListener('DOMContentLoaded', () => {{
                const originalRender = renderApp;
                const TARGET_FILTER = "{league_filter.lower()}";
                const IS_LEAGUE_TYPE = {str(is_league_type).lower()};
                
                // Override the render function or hook into data
                // Since we can't easily hook, we will use CSS to hide irrelevant things 
                // and a MutationObserver or just reliance on the modified PRIORITIES list above.
                
                // HIDE TRENDING LIVE (Since it might show other sports)
                const liveSec = document.getElementById('live-section');
                if(liveSec) liveSec.style.display = 'none';
                
                // The 'upcoming-container' will naturally only show our league 
                // because we passed only this league in {{JS_PRIORITIES}}.
                // However, the 'Leftovers' (Generic) section might appear.
                // We need to suppress leftovers.
            }});
        </script>
        <style>
            /* Hide any section that isn't our target */
            /* Actually, simply passing single priority works for the grouped section. 
               We just need to hide the generic leftovers. */
        </style>
        """
        html = html.replace('</body>', filter_script + '</body>')

    else:
        # Standard Home/Page
        html = html.replace('{{JS_PRIORITIES}}', json.dumps(priorities))

    # 6. Schemas
    schemas = []
    # Organization Schema (Static)
    if page_data.get('schemas', {}).get('org'):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": f"{p1}{p2}",
            "url": f"https://{domain}",
            "logo": s.get('logo_url')
        })
    
    # We don't inject Live/Upcoming schemas here because they are Dynamic (handled by Frontend JS)
    # However, if the user unchecked them in Admin, we could inject a JS var to disable them.
    # For now, we assume frontend always handles them if enabled.
    
    if schemas:
        schema_script = f'<script type="application/ld+json">{json.dumps(schemas)}</script>'
        html = html.replace('{{SCHEMA_BLOCK}}', schema_script)
    else:
        html = html.replace('{{SCHEMA_BLOCK}}', '')

    return html

def build_site():
    print("--- 🔨 Starting Build Process ---")
    
    config = load_json(CONFIG_PATH)
    if not config:
        print("❌ Config not found!")
        return

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    # 1. BUILD CUSTOM PAGES (Home + Others)
    print("📄 Building Pages...")
    for page in config.get('pages', []):
        slug = page.get('slug')
        print(f"   - Processing: {page.get('title')} (/{slug})")
        
        final_html = render_page(template, config, page)
        
        if slug == 'home':
            out_path = os.path.join(OUTPUT_DIR, 'index.html')
        else:
            # Create directory for clean URL: slug/index.html
            dir_path = os.path.join(OUTPUT_DIR, slug)
            os.makedirs(dir_path, exist_ok=True)
            out_path = os.path.join(dir_path, 'index.html')
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

    # 2. BUILD AUTOMATIC LEAGUE PAGES
    print("🏆 Building League Pages...")
    country = config.get('site_settings', {}).get('target_country', 'US')
    priorities = config.get('sport_priorities', {}).get(country, {})
    
    for name, data in priorities.items():
        # Handle new object structure or legacy number
        if isinstance(data, int): data = {'score': data, 'isLeague': False, 'hasLink': False}
        
        if data.get('hasLink'):
            print(f"   - Generating League Page: {name}")
            
            # Prepare Page Data
            slug = slugify(name)
            page_data = {
                'title': f"{name} Live Streams",
                'meta_title': f"Watch {name} Live Free - {config['site_settings'].get('domain')}",
                'meta_desc': f"The best source for {name} live streams. Watch high quality {name} matches free.",
                'layout': 'league', # Custom layout logic in render_page
                'content': f"<h2>{name} Schedule</h2><p>Check below for the latest upcoming {name} matches.</p>",
                'schemas': {'org': True}
            }
            
            final_html = render_page(template, config, page_data, is_league_page=True, league_filter=name)
            
            # Save to league/slug/index.html
            dir_path = os.path.join(OUTPUT_DIR, 'league', slug)
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(final_html)

    print("✅ Build Complete!")

if __name__ == "__main__":
    build_site()
