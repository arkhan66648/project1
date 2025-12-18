import json
import time
import requests
import os
import base64
from datetime import datetime

# ==========================================
# 1. THEME PRESETS (Professional Colors)
# ==========================================
THEMES = {
    "red": {
        "brand_primary": "#D00000",
        "brand_dark": "#8a0000",
        "accent": "#FFD700",
        "status": "#00e676"
    },
    "blue": {
        "brand_primary": "#0056D2",
        "brand_dark": "#003c96",
        "accent": "#00C2CB",
        "status": "#00e676"
    },
    "green": {
        "brand_primary": "#008f39",
        "brand_dark": "#006428",
        "accent": "#BBF7D0",
        "status": "#22c55e"
    },
    "purple": {
        "brand_primary": "#7C3AED",
        "brand_dark": "#5B21B6",
        "accent": "#F472B6",
        "status": "#34d399"
    }
}

# Standard Config Load
def load_config():
    with open('data/config.json', 'r') as f:
        return json.load(f)

# ... [Keep your fetch_streamed_pk, fetch_topembed, obfuscate_link, merge_matches functions EXACTLY as they were in previous steps] ...

# ... [Include process_data function from previous steps] ...

# ==========================================
# NEW: STATIC HTML GENERATOR
# ==========================================
def generate_html(data, config):
    # 1. Select Theme (Default to Red if not set)
    selected_theme = config.get('theme_color', 'red')
    colors = THEMES.get(selected_theme, THEMES['red'])

    # 2. Build Navigation HTML (Server Side for Speed)
    # This loops through your site_links and builds the <a> tags
    nav_html = ""
    for link in config['site_links']:
        slug = link['slug'].strip('/')
        # Determine if we are at root or subpage later, 
        # but for static build we usually assume relative paths
        nav_html += f'<a href="/{slug}">{link["title"]}</a>\n'

    # 3. Build Static Schema (WebSite + Organization)
    # We bake this into the HTML so Google sees it immediately
    static_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": config['site_settings']['site_name'],
                "url": f"https://{config['site_settings']['domain']}",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"https://{config['site_settings']['domain']}/?q={{search_term_string}}",
                    "query-input": "required name=search_term_string"
                }
            },
            {
                "@type": "Organization",
                "name": config['site_settings']['site_name'],
                "url": f"https://{config['site_settings']['domain']}",
                "logo": config['site_settings']['logo_url'],
                "sameAs": config.get('social_links', [])
            }
        ]
    }
    static_schema_json = json.dumps(static_schema)

    # 4. Load Your Master Template
    # We expect your design to be saved as 'assets/master_template.html'
    try:
        with open('assets/master_template.html', 'r') as f:
            html = f.read()
    except FileNotFoundError:
        print("Master template not found!")
        return

    # 5. INJECT VARIABLES (The Magic)
    
    # CSS Colors
    html = html.replace('{{BRAND_PRIMARY}}', colors['brand_primary'])
    html = html.replace('{{BRAND_DARK}}', colors['brand_dark'])
    html = html.replace('{{ACCENT}}', colors['accent'])
    html = html.replace('{{STATUS}}', colors['status'])
    
    # Content
    s = config['site_settings']
    html = html.replace('{{SITE_NAME}}', s['site_name'])
    html = html.replace('{{META_TITLE}}', s['meta_title'])
    html = html.replace('{{META_DESC}}', s['meta_desc'])
    html = html.replace('{{LOGO_URL}}', s['logo_url'])
    html = html.replace('{{DOMAIN}}', s['domain'])
    
    # Navigation & Article
    html = html.replace('{{NAV_LINKS}}', nav_html)
    
    # Home Article (Load from file if exists)
    try:
        with open('data/articles/home.html', 'r') as af:
            html = html.replace('{{HOMEPAGE_ARTICLE}}', af.read())
    except:
        html = html.replace('{{HOMEPAGE_ARTICLE}}', "<p>Welcome to the #1 Streaming Site.</p>")

    # Schema Injection
    html = html.replace('{{STATIC_SCHEMA}}', static_schema_json)

    # 6. Save as index.html
    with open('index.html', 'w') as f:
        f.write(html)
    print("Generated Optimized index.html")

    # 7. Generate Sub-Pages (Similar logic, just updated paths)
    # [You can adapt the previous generate_pages function here using the same logic]

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    conf = load_config()
    # ... Fetch, Merge, Process logic ...
    # final_json = ...
    
    # Save Data
    with open('data/matches.json', 'w') as f:
        json.dump(final_json, f)
        
    # Generate HTML
    generate_html(final_json, conf)
