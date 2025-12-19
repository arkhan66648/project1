const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';       
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

const CATEGORIES = [
    "NFL", "NBA", "UFC", "MLB", "NHL", "Soccer", "F1", "Boxing", "Golf", "Tennis",
    "Premier League", "Champions League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "NCAA Football", "NCAA Basketball"
];

let configData = {
    pages: [], site_settings: {}, theme: {}, targeting: {}, wildcard: {},
    social_stats: {}, api_keys: {}, header_menu: [], hero_categories: [],
    footer_league_menu: [], footer_static_menu: []
};
let currentSha = null;
let activePageIndex = -1;

// ==========================================
// INITIALIZATION
// ==========================================
window.addEventListener("DOMContentLoaded", () => {
    // 1. Sidebar Toggle
    document.getElementById('sidebarToggle').onclick = () => 
        document.getElementById('sidebar').classList.toggle('minimized');

    // 2. Dropdowns
    const wcSelect = document.getElementById('wcCategory');
    const pCatAssign = document.getElementById('pCategoryAssign');
    CATEGORIES.forEach(cat => {
        const opt1 = new Option(cat, cat);
        const opt2 = new Option(cat, cat);
        wcSelect.add(opt1);
        pCatAssign.add(opt2);
    });

    // 3. Schema Toggles
    ['schOrgEnable', 'schFaqEnable'].forEach(id => {
        document.getElementById(id).addEventListener('change', (e) => {
            const box = document.getElementById(id.replace('Enable', 'Box'));
            if(e.target.checked) box.style.display = 'block'; else box.style.display = 'none';
        });
    });

    // 4. Init TinyMCE
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#tinymce-editor',
            height: 400,
            skin: "oxide-dark",
            content_css: "dark",
            plugins: 'code table lists link',
            toolbar: 'undo redo | blocks | bold italic | link | align | code',
            setup: (editor) => {
                editor.on('change', () => {
                    if(activePageIndex > -1) configData.pages[activePageIndex].content = editor.getContent();
                });
            }
        });
    }

    // 5. Input Listeners (Fixing New Page Input Bug)
    ['pSlug', 'pH1', 'pType'].forEach(id => {
        document.getElementById(id).addEventListener('input', () => {
            if(activePageIndex > -1) {
                const p = configData.pages[activePageIndex];
                if(id === 'pSlug' && p.slug !== 'home') p.slug = document.getElementById(id).value;
                if(id === 'pH1') p.h1 = document.getElementById(id).value;
                if(id === 'pType') p.type = document.getElementById(id).value;
                renderPageList(); // Refresh list to reflect changes immediately
            }
        });
    });

    // 6. Auth
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();
    
    // Live Font Preview
    ['fontFamily','titleP1','titleP2','colT1','colT2','titleItalic'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.addEventListener('input', updatePreview);
    });
});

// ==========================================
// CORE DATA
// ==========================================
async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    document.getElementById('statusMsg').textContent = "⏳ Loading...";
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        if (res.status === 404) {
            alert("Config not found. Initializing new defaults.");
            ensureStructure(); populateUI(); return;
        }
        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        ensureStructure();
        populateUI();
        document.getElementById('statusMsg').textContent = "✅ System Ready";
    } catch (e) { alert("Load Error: " + e.message); }
}

function ensureStructure() {
    if(!configData.pages) configData.pages = [];
    if(!configData.header_menu) configData.header_menu = [];
    if(!configData.hero_categories) configData.hero_categories = [];
    if(!configData.footer_league_menu) configData.footer_league_menu = [];
    if(!configData.footer_static_menu) configData.footer_static_menu = [];
    if(!configData.targeting) configData.targeting = { country: 'USA', timezone: 'US/Eastern' };
    if(!configData.wildcard) configData.wildcard = { category: '', id: '', fallback: '' };
}

function populateUI() {
    const s = configData.site_settings || {};
    const t = configData.theme || {};
    const wc = configData.wildcard || {};
    const soc = configData.social_stats || {};

    setVal('titleP1', s.title_part_1); setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain); setVal('logoUrl', s.logo_url);
    setVal('faviconUrl', s.favicon); setVal('gaId', s.ga_id);
    setVal('customMeta', s.custom_meta); setVal('footerKw', (s.footer_keywords||[]).join(', '));
    setVal('apiStreamed', configData.api_keys?.streamed_url);
    setVal('apiTopembed', configData.api_keys?.topembed_url);

    setVal('tgtCountry', configData.targeting.country);
    setVal('tgtTimezone', configData.targeting.timezone);
    setVal('wcCategory', wc.category); setVal('wcId', wc.id); setVal('wcFallback', wc.fallback);

    setColor('colPrimary', 'txtPrimary', t.brand_primary);
    setColor('colDark', 'txtDark', t.brand_dark);
    setColor('colGold', 'txtGold', t.accent_gold);
    setColor('colStatus', 'txtStatus', t.status_green);
    setColor('colBg', 'txtBg', t.bg_body);
    setColor('colHeroStart', 'txtHeroStart', t.hero_gradient_start);
    setColor('colTrendStart', 'txtTrendStart', t.trend_gradient_start);
    setColor('colFooter', 'txtFooter', t.footer_bg);
    setVal('fontFamily', t.font_family);
    setColor('colT1', 'txtT1', t.title_color_1);
    setColor('colT2', 'txtT2', t.title_color_2);
    if(document.getElementById('titleItalic')) document.getElementById('titleItalic').checked = t.title_italic || false;

    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    renderPageList();
    renderAllMenus();
    updatePreview();
}

// ==========================================
// PAGE MANAGER (Improved)
// ==========================================
function renderPageList() {
    const list = document.getElementById('pagesList');
    list.innerHTML = '';
    configData.pages.forEach((p, i) => {
        const div = document.createElement('div');
        div.className = `page-item ${i === activePageIndex ? 'active' : ''}`;
        div.innerHTML = `<strong>${p.h1 || p.slug}</strong> <small>/${p.slug}</small>`;
        div.onclick = () => loadPage(i);
        list.appendChild(div);
    });
}

function loadPage(i) {
    activePageIndex = i;
    const p = configData.pages[i];
    renderPageList();
    
    document.getElementById('pageEditor').style.display = 'flex';
    document.getElementById('editHeading').innerText = `Editing: ${p.slug}`;
    
    const slugIn = document.getElementById('pSlug');
    if(p.slug === 'home') { slugIn.disabled = true; document.getElementById('btnDeletePage').style.display='none'; }
    else { slugIn.disabled = false; document.getElementById('btnDeletePage').style.display='block'; }

    setVal('pSlug', p.slug); setVal('pType', p.type); setVal('pCategoryAssign', p.assigned_category);
    setVal('pH1', p.h1); setVal('pHero', p.hero_text);
    setVal('pMetaTitle', p.meta_title); setVal('pMetaDesc', p.meta_desc);
    
    if(tinymce.get('tinymce-editor')) tinymce.get('tinymce-editor').setContent(p.content || '');

    // Load Schemas
    const sch = p.schemas || {};
    document.getElementById('schOrgEnable').checked = !!sch.organization;
    document.getElementById('schOrgBox').style.display = sch.organization ? 'block' : 'none';
    if(sch.organization) {
        setVal('schOrgName', sch.organization.name);
        setVal('schOrgLogo', sch.organization.logo);
        setVal('schOrgSocials', sch.organization.socials);
    } else { setVal('schOrgName', ''); setVal('schOrgLogo', ''); setVal('schOrgSocials', ''); }

    document.getElementById('schFaqEnable').checked = !!sch.faq;
    document.getElementById('schFaqBox').style.display = sch.faq ? 'block' : 'none';
    document.getElementById('faqContainer').innerHTML = '';
    if(sch.faq) {
        (sch.faq.items || []).forEach(item => addFaqItem(item.q, item.a));
    }
}

window.createNewPage = function() {
    const newPage = { slug: 'new-page-' + Date.now(), h1: 'New Page', type: 'static', content: '', schemas: {} };
    configData.pages.push(newPage);
    loadPage(configData.pages.length - 1);
};

// CRITICAL: Deletes folder from GitHub
window.deleteCurrentPage = async function() {
    if(activePageIndex === -1) return;
    const p = configData.pages[activePageIndex];
    if(p.slug === 'home') return;

    if(!confirm(`Delete /${p.slug}? This will delete the folder from GitHub immediately.`)) return;

    const token = localStorage.getItem('gh_token');
    // Try to delete file
    const path = `${p.slug}/index.html`;
    try {
        const getRes = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        if(getRes.ok) {
            const fileData = await getRes.json();
            await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}`, {
                method: 'DELETE',
                headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: `Deleted ${p.slug}`, sha: fileData.sha, branch: BRANCH })
            });
        }
    } catch(e) { console.warn("GitHub deletion skipped/failed", e); }

    configData.pages.splice(activePageIndex, 1);
    activePageIndex = -1;
    document.getElementById('pageEditor').style.display = 'none';
    renderPageList();
};

window.saveCurrentPageLocal = function() {
    if(activePageIndex === -1) return;
    const p = configData.pages[activePageIndex];
    
    if(p.slug !== 'home') p.slug = getVal('pSlug');
    p.type = getVal('pType'); p.assigned_category = getVal('pCategoryAssign');
    p.h1 = getVal('pH1'); p.hero_text = getVal('pHero');
    p.meta_title = getVal('pMetaTitle'); p.meta_desc = getVal('pMetaDesc');
    if(tinymce.get('tinymce-editor')) p.content = tinymce.get('tinymce-editor').getContent();

    // Save Schemas
    p.schemas = {};
    if(document.getElementById('schOrgEnable').checked) {
        p.schemas.organization = {
            name: getVal('schOrgName'), logo: getVal('schOrgLogo'), socials: getVal('schOrgSocials')
        };
    }
    if(document.getElementById('schFaqEnable').checked) {
        const items = [];
        document.querySelectorAll('.faq-item').forEach(el => {
            items.push({ q: el.querySelector('.faq-q').value, a: el.querySelector('.faq-a').value });
        });
        p.schemas.faq = { items };
    }

    renderPageList();
    alert("Page Saved Locally. Click 'Save All Changes' to Publish.");
};

window.addFaqItem = function(q='', a='') {
    const div = document.createElement('div');
    div.className = 'faq-item';
    div.style.marginBottom = '10px';
    div.innerHTML = `
        <input type="text" class="faq-q" placeholder="Question" value="${q}" style="margin-bottom:5px;">
        <textarea class="faq-a" placeholder="Answer" rows="2" style="margin-bottom:5px;">${a}</textarea>
        <button class="btn-x" onclick="this.parentElement.remove()" style="float:right;">🗑️</button>
        <div style="clear:both"></div>`;
    document.getElementById('faqContainer').appendChild(div);
};

// ==========================================
// MENUS
// ==========================================
function renderAllMenus() {
    renderMenuSection('header', configData.header_menu);
    renderMenuSection('hero', configData.hero_categories);
    renderMenuSection('footer_league', configData.footer_league_menu);
    renderMenuSection('footer_static', configData.footer_static_menu);
}

function renderMenuSection(id, items) {
    const cont = document.getElementById(`menu-${id}`);
    if(!cont) return;
    cont.innerHTML = items.map((item, idx) => `
        <div class="menu-item-row">
            <div>
                <strong>${item.title}</strong>
                <span style="color:#666; font-size:0.8rem; margin-left:5px;">${item.url}</span>
            </div>
            <button class="btn-x" onclick="deleteMenuItem('${id}', ${idx})">×</button>
        </div>
    `).join('');
}

window.openMenuModal = function(section) {
    document.getElementById('menuTargetSection').value = section;
    setVal('menuTitleItem', ''); setVal('menuUrlItem', '');
    document.getElementById('menuModal').style.display = 'flex';
};

window.updateMenuInput = function() {
    const type = document.getElementById('menuLinkType').value;
    const ctr = document.getElementById('menuInputContainer');
    ctr.innerHTML = '';

    if (type === 'custom') {
        ctr.innerHTML = `<label>URL</label><input type="text" id="menuUrlItem">`;
    } else if (type === 'page') {
        let opts = `<option value="">Select Page...</option>`;
        configData.pages.forEach(p => {
            const url = p.slug === 'home' ? '/' : `/${p.slug}/`;
            opts += `<option value="${url}">${p.slug}</option>`;
        });
        ctr.innerHTML = `<label>Select Page</label><select id="menuUrlItem">${opts}</select>`;
    } else if (type === 'category') {
        let opts = `<option value="">Select Category...</option>`;
        CATEGORIES.forEach(c => {
            const folder = c.toLowerCase().replace(/ /g, '-');
            opts += `<option value="/${folder}/">${c}</option>`;
        });
        ctr.innerHTML = `<label>Select Category</label><select id="menuUrlItem">${opts}</select>`;
    } else if (type === 'wildcard') {
        const wcId = getVal('wcId') || 'wildcard';
        ctr.innerHTML = `<label>Anchor</label><input type="text" id="menuUrlItem" value="#${wcId}" disabled>`;
    }
};

window.saveMenuItem = function() {
    const section = document.getElementById('menuTargetSection').value;
    const title = getVal('menuTitleItem');
    const url = getVal('menuUrlItem');
    const hl = document.getElementById('menuHighlight').checked;

    if(!title || !url) return alert("Required fields missing");

    const item = { title, url, highlight: hl };
    if(section === 'header') configData.header_menu.push(item);
    if(section === 'hero') configData.hero_categories.push(item);
    if(section === 'footer_league') configData.footer_league_menu.push(item);
    if(section === 'footer_static') configData.footer_static_menu.push(item);

    renderAllMenus();
    document.getElementById('menuModal').style.display = 'none';
};

window.deleteMenuItem = function(section, idx) {
    if(section === 'header') configData.header_menu.splice(idx, 1);
    if(section === 'hero') configData.hero_categories.splice(idx, 1);
    if(section === 'footer_league') configData.footer_league_menu.splice(idx, 1);
    if(section === 'footer_static') configData.footer_static_menu.splice(idx, 1);
    renderAllMenus();
};

// ==========================================
// SAVING
// ==========================================
document.getElementById('saveBtn').onclick = async () => {
    const btn = document.getElementById('saveBtn');
    btn.disabled = true; document.getElementById('statusMsg').textContent = "Uploading...";

    // Capture Core Data
    configData.site_settings.title_part_1 = getVal('titleP1');
    configData.site_settings.title_part_2 = getVal('titleP2');
    configData.site_settings.domain = getVal('siteDomain');
    configData.site_settings.logo_url = getVal('logoUrl');
    configData.site_settings.favicon = getVal('faviconUrl');
    configData.site_settings.ga_id = getVal('gaId');
    configData.site_settings.custom_meta = getVal('customMeta');
    configData.site_settings.footer_keywords = getVal('footerKw').split(',');

    configData.targeting = { country: getVal('tgtCountry'), timezone: getVal('tgtTimezone') };
    configData.wildcard = { category: getVal('wcCategory'), id: getVal('wcId'), fallback: getVal('wcFallback') };
    
    configData.theme.brand_primary = getVal('colPrimary');
    configData.theme.brand_dark = getVal('colDark');
    configData.theme.accent_gold = getVal('colGold');
    configData.theme.status_green = getVal('colStatus');
    configData.theme.bg_body = getVal('colBg');
    configData.theme.hero_gradient_start = getVal('colHeroStart');
    configData.theme.trend_gradient_start = getVal('colTrendStart');
    configData.theme.footer_bg = getVal('colFooter');
    configData.theme.font_family = getVal('fontFamily');
    configData.theme.title_color_1 = getVal('colT1');
    configData.theme.title_color_2 = getVal('colT2');
    configData.theme.title_italic = document.getElementById('titleItalic').checked;

    configData.social_stats.telegram = getVal('socTelegram');
    configData.social_stats.twitter = getVal('socTwitter');
    configData.social_stats.discord = getVal('socDiscord');
    configData.social_stats.reddit = getVal('socReddit');

    configData.api_keys.streamed_url = getVal('apiStreamed');
    configData.api_keys.topembed_url = getVal('apiTopembed');

    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Update Config", content: content, sha: currentSha, branch: BRANCH })
        });
        document.getElementById('statusMsg').textContent = "✅ Saved!";
        alert("Configuration saved! Your changes will be live shortly.");
    } catch(e) { alert("Error: " + e.message); }
    btn.disabled = false;
};

// UI Helpers
window.switchTab = function(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
};
window.saveToken = function() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); loadConfig(); document.getElementById('authModal').style.display='none'; };
window.setVal = function(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; };
window.getVal = function(id) { return document.getElementById(id)?.value || ""; };
window.setColor = function(pid, tid, v) { setVal(pid, v); setVal(tid, v); };
window.updatePreview = function() {
    const prev = document.getElementById('fontPreview');
    if(!prev) return;
    prev.style.fontFamily = getVal('fontFamily');
    prev.innerHTML = `<span style="color:${getVal('colT1')}">${getVal('titleP1') || 'Stream'}</span><span style="color:${getVal('colT2')}">${getVal('titleP2') || 'East'}</span>`;
    prev.style.fontStyle = document.getElementById('titleItalic').checked ? 'italic' : 'normal';
};
function applyTheme(name) {
    const t = THEMES[name]; if(!t) return;
    setColor('colPrimary', 'txtPrimary', t.primary); setColor('colDark', 'txtDark', t.dark);
    setColor('colGold', 'txtGold', t.accent); setColor('colStatus', 'txtStatus', t.status);
    setColor('colBg', 'txtBg', t.bg); setColor('colT1', 'txtT1', t.t1); setColor('colT2', 'txtT2', t.t2);
    updatePreview();
}
