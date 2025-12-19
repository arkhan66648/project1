// ==========================================
// CONFIGURATION
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';       
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// Categories for Dropdowns
const CATEGORIES = [
    "NFL", "NBA", "UFC", "MLB", "NHL", "Soccer", "F1", "Boxing", "Golf", "Tennis",
    "Premier League", "Champions League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"
];

const THEMES = {
    red: { primary: "#D00000", dark: "#8a0000", accent: "#FFD700", status: "#00e676", bg: "#050505", t1: "#ffffff", t2: "#D00000" },
    blue: { primary: "#0056D2", dark: "#003c96", accent: "#00C2CB", status: "#00e676", bg: "#050505", t1: "#ffffff", t2: "#0056D2" },
    green: { primary: "#008f39", dark: "#006428", accent: "#BBF7D0", status: "#22c55e", bg: "#050505", t1: "#ffffff", t2: "#008f39" },
    purple: { primary: "#7C3AED", dark: "#5B21B6", accent: "#F472B6", status: "#34d399", bg: "#050505", t1: "#ffffff", t2: "#7C3AED" }
};

let currentSha = null;
let configData = {
    pages: [], 
    site_settings: {}, 
    theme: {}, 
    targeting: {}, 
    wildcard: {},
    social_stats: {}, 
    api_keys: {}, 
    // 4 Menu Arrays
    header_menu: [],
    hero_categories: [],
    footer_league_menu: [],
    footer_static_menu: []
};
let activePageIndex = -1;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Sidebar Toggle
    const toggle = document.getElementById('sidebarToggle');
    if(toggle) toggle.addEventListener('click', () => document.getElementById('sidebar').classList.toggle('minimized'));

    // 2. Populate Dropdowns (Wildcard & Page Assign)
    const wcSelect = document.getElementById('wcCategory');
    const pCatAssign = document.getElementById('pCategoryAssign');
    CATEGORIES.forEach(cat => {
        // Wildcard Dropdown
        const opt1 = document.createElement('option');
        opt1.value = cat; opt1.innerText = cat;
        wcSelect.appendChild(opt1);
        
        // Page Assignment Dropdown
        const opt2 = document.createElement('option');
        opt2.value = cat; opt2.innerText = cat;
        pCatAssign.appendChild(opt2);
    });

    // 3. Init TinyMCE
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#tinymce-editor',
            height: 500, // Taller editor
            skin: "oxide-dark",
            content_css: "dark",
            plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount code',
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline | link image media table | align | code',
            setup: (editor) => { editor.on('change', () => { if(activePageIndex > -1) configData.pages[activePageIndex].content = editor.getContent(); }); }
        });
    }

    // 4. Schema Toggles
    ['schOrgEnable', 'schFaqEnable'].forEach(id => {
        document.getElementById(id).addEventListener('change', (e) => {
            const box = document.getElementById(id.replace('Enable', 'Box'));
            if(e.target.checked) box.classList.remove('hidden'); else box.classList.add('hidden');
        });
    });

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();

    // Live Preview
    ['fontFamily','titleP1','titleP2','colT1','colT2','titleItalic'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.addEventListener('input', updatePreview);
    });
});

function updatePreview() {
    const prev = document.getElementById('fontPreview');
    if(!prev) return;
    prev.style.fontFamily = getVal('fontFamily');
    prev.innerHTML = `<span style="color:${getVal('colT1')}">${getVal('titleP1') || 'Stream'}</span><span style="color:${getVal('colT2')}">${getVal('titleP2') || 'East'}</span>`;
    prev.style.fontStyle = document.getElementById('titleItalic').checked ? 'italic' : 'normal';
}

// ==========================================
// DATA LOADING
// ==========================================
async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    const msg = document.getElementById('statusMsg');
    msg.textContent = "⏳ Loading...";

    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });

        if (res.status === 404) {
            msg.textContent = "🆕 New Config";
            currentSha = null;
            populateUI(configData); 
            return;
        }

        if (!res.ok) throw new Error(`GitHub API Error: ${res.status}`);

        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        
        // Ensure defaults
        if(!configData.pages) configData.pages = [];
        if(!configData.header_menu) configData.header_menu = [];
        if(!configData.hero_categories) configData.hero_categories = [];
        if(!configData.footer_league_menu) configData.footer_league_menu = [];
        if(!configData.footer_static_menu) configData.footer_static_menu = [];

        populateUI(configData);
        msg.textContent = "✅ Ready";

    } catch (err) { 
        console.error(err); 
        msg.textContent = "❌ Load Error";
    }
}

function populateUI(data) {
    const s = data.site_settings || {};
    const t = data.theme || {};
    const tgt = data.targeting || {};
    const wc = data.wildcard || {};
    const soc = data.social_stats || {};
    const api = data.api_keys || {};

    // General
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('faviconUrl', s.favicon);
    setVal('gaId', s.ga_id);
    setVal('customMeta', s.custom_meta);
    setVal('footerKw', (s.footer_keywords || []).join(', '));
    setVal('apiStreamed', api.streamed_url);
    setVal('apiTopembed', api.topembed_url);

    // Targeting
    setVal('tgtCountry', tgt.country || 'USA');
    setVal('tgtTimezone', tgt.timezone || 'US/Eastern');
    setVal('wcCategory', wc.category);
    setVal('wcId', wc.id);
    setVal('wcFallback', wc.fallback);
    document.getElementById('currentStrategy').innerText = tgt.country === 'UK' ? "UK Focused" : "USA Focused";

    // Appearance
    setColor('colPrimary', 'txtPrimary', t.brand_primary || '#D00000');
    setColor('colDark', 'txtDark', t.brand_dark || '#8a0000');
    setColor('colGold', 'txtGold', t.accent_gold || '#FFD700');
    setColor('colStatus', 'txtStatus', t.status_green || '#00e676');
    setColor('colBg', 'txtBg', t.bg_body || '#050505');
    setColor('colHeroStart', 'txtHeroStart', t.hero_gradient_start || '#1a0505');
    setColor('colTrendStart', 'txtTrendStart', t.trend_gradient_start || '#140000');
    setColor('colFooter', 'txtFooter', t.footer_bg || '#000000');
    setVal('fontFamily', t.font_family);
    setColor('colT1', 'txtT1', t.title_color_1);
    setColor('colT2', 'txtT2', t.title_color_2);
    if(document.getElementById('titleItalic')) document.getElementById('titleItalic').checked = t.title_italic || false;

    // Socials
    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    // Render 4 Menus
    renderMenuSection('header', configData.header_menu);
    renderMenuSection('hero', configData.hero_categories);
    renderMenuSection('footer-league', configData.footer_league_menu);
    renderMenuSection('footer-static', configData.footer_static_menu);

    // Pages
    renderPageList();
    updatePreview();
}

// ==========================================
// MENU MANAGER (SMART DROPDOWNS)
// ==========================================
function renderMenuSection(id, items) {
    const container = document.getElementById(`menu-${id}`);
    if(!container) return;
    container.innerHTML = '';
    
    items.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'menu-list-item';
        const hl = item.highlight ? '★ ' : '';
        div.innerHTML = `
            <span>${hl}<strong>${item.title}</strong> <small>${item.url}</small></span>
            <button class="btn-delete" onclick="deleteMenuItem('${id}', ${idx})">✕</button>
        `;
        container.appendChild(div);
    });
}

function openMenuModal(section) {
    document.getElementById('menuTargetSection').value = section;
    setVal('menuTitleItem', '');
    setVal('menuUrlItem', '');
    document.getElementById('menuLinkType').value = 'custom';
    document.getElementById('menuHighlight').checked = false;
    updateMenuInput();
    document.getElementById('menuModal').style.display = 'flex';
}

function updateMenuInput() {
    const type = document.getElementById('menuLinkType').value;
    const container = document.getElementById('menuInputContainer');
    container.innerHTML = '';

    if (type === 'custom') {
        container.innerHTML = `<input type="text" id="menuUrlItem" placeholder="https://...">`;
    } else if (type === 'page') {
        let opts = `<option value="">Select Page...</option>`;
        configData.pages.forEach(p => {
            const url = p.slug === 'home' ? '/' : `/${p.slug}/`;
            opts += `<option value="${url}">${p.slug}</option>`;
        });
        container.innerHTML = `<select id="menuUrlItem">${opts}</select>`;
    } else if (type === 'category') {
        let opts = `<option value="">Select Category...</option>`;
        CATEGORIES.forEach(c => {
            const folder = c.toLowerCase().replace(/ /g, '-');
            opts += `<option value="/${folder}/">${c}</option>`;
        });
        container.innerHTML = `<select id="menuUrlItem">${opts}</select>`;
    } else if (type === 'wildcard') {
        const wcId = getVal('wcId') || 'wildcard';
        container.innerHTML = `<input type="text" id="menuUrlItem" value="#${wcId}" disabled style="opacity:0.7">`;
    }
}

function saveMenuItem() {
    const section = document.getElementById('menuTargetSection').value;
    const title = getVal('menuTitleItem');
    const type = document.getElementById('menuLinkType').value;
    let url = getVal('menuUrlItem');
    const highlight = document.getElementById('menuHighlight').checked;

    if(type === 'wildcard') url = '#' + (getVal('wcId') || 'wildcard');

    if(!title || !url) { alert("Title and Destination are required."); return; }

    const item = { title, url, highlight };

    if(section === 'header') configData.header_menu.push(item);
    if(section === 'hero') configData.hero_categories.push(item);
    if(section === 'footer_league') configData.footer_league_menu.push(item);
    if(section === 'footer_static') configData.footer_static_menu.push(item);

    // Refresh UI
    renderMenuSection(section.replace('_','-'), 
        section==='header' ? configData.header_menu : 
        section==='hero' ? configData.hero_categories :
        section==='footer_league' ? configData.footer_league_menu : configData.footer_static_menu
    );
    
    document.getElementById('menuModal').style.display = 'none';
}

function deleteMenuItem(sectionId, idx) {
    let arr = null;
    if(sectionId === 'header') arr = configData.header_menu;
    if(sectionId === 'hero') arr = configData.hero_categories;
    if(sectionId === 'footer-league') arr = configData.footer_league_menu;
    if(sectionId === 'footer-static') arr = configData.footer_static_menu;
    
    if(arr) {
        arr.splice(idx, 1);
        renderMenuSection(sectionId, arr);
    }
}

// ==========================================
// PAGE MANAGER (SCHEMAS & EDITOR)
// ==========================================
function renderPageList() {
    const list = document.getElementById('pagesList');
    list.innerHTML = '';
    configData.pages.forEach((page, index) => {
        const div = document.createElement('div');
        div.className = `page-list-item ${index === activePageIndex ? 'active' : ''}`;
        div.innerHTML = `<strong>${page.slug}</strong> <small>(${page.type})</small>`;
        div.onclick = () => loadPageToEditor(index);
        list.appendChild(div);
    });
}

function loadPageToEditor(index) {
    activePageIndex = index;
    const page = configData.pages[index];
    renderPageList(); 
    
    document.getElementById('pageEditor').style.display = 'flex';
    document.getElementById('editHeading').innerText = `Editing: ${page.slug}`;
    
    // Slug Logic
    const slugInput = document.getElementById('pSlug');
    if(page.slug === 'home') {
        slugInput.disabled = true;
        document.getElementById('btnDeletePage').style.display = 'none';
    } else {
        slugInput.disabled = false;
        document.getElementById('btnDeletePage').style.display = 'block';
    }

    setVal('pSlug', page.slug);
    setVal('pType', page.type);
    setVal('pCategoryAssign', page.assigned_category); // New
    setVal('pH1', page.h1);
    setVal('pHero', page.hero_text);
    setVal('pMetaTitle', page.meta_title);
    setVal('pMetaDesc', page.meta_desc);
    
    if(tinymce.get('tinymce-editor')) tinymce.get('tinymce-editor').setContent(page.content || '');

    // Load Schemas
    const sch = page.schemas || {};
    
    // Org
    document.getElementById('schOrgEnable').checked = !!sch.organization;
    if(sch.organization) {
        document.getElementById('schOrgBox').classList.remove('hidden');
        setVal('schOrgName', sch.organization.name);
        setVal('schOrgLogo', sch.organization.logo);
        setVal('schOrgSocials', sch.organization.socials);
    } else {
        document.getElementById('schOrgBox').classList.add('hidden');
        setVal('schOrgName', ''); setVal('schOrgLogo', ''); setVal('schOrgSocials', '');
    }

    // FAQ
    document.getElementById('schFaqEnable').checked = !!sch.faq;
    const faqContainer = document.getElementById('faqContainer');
    faqContainer.innerHTML = '';
    if(sch.faq) {
        document.getElementById('schFaqBox').classList.remove('hidden');
        (sch.faq.items || []).forEach(item => addFaqItem(item.q, item.a));
    } else {
        document.getElementById('schFaqBox').classList.add('hidden');
    }
}

function addFaqItem(q='', a='') {
    const div = document.createElement('div');
    div.className = 'faq-item';
    div.style.marginBottom = '10px';
    div.innerHTML = `
        <input type="text" class="faq-q" placeholder="Question" value="${q}">
        <textarea class="faq-a" placeholder="Answer" rows="2">${a}</textarea>
        <button class="btn-delete" onclick="this.parentElement.remove()" style="width:auto; float:right;">Delete</button>
        <div style="clear:both"></div>
    `;
    document.getElementById('faqContainer').appendChild(div);
}

function saveCurrentPageLocal() {
    if(activePageIndex === -1) return;
    const page = configData.pages[activePageIndex];
    
    if(page.slug !== 'home') page.slug = getVal('pSlug');
    page.type = getVal('pType');
    page.assigned_category = getVal('pCategoryAssign'); // New
    page.h1 = getVal('pH1');
    page.title = getVal('pH1'); 
    page.hero_text = getVal('pHero');
    page.meta_title = getVal('pMetaTitle');
    page.meta_desc = getVal('pMetaDesc');
    if(tinymce.get('tinymce-editor')) page.content = tinymce.get('tinymce-editor').getContent();
    
    // Save Schemas
    page.schemas = {};
    if(document.getElementById('schOrgEnable').checked) {
        page.schemas.organization = {
            name: getVal('schOrgName'),
            logo: getVal('schOrgLogo'),
            socials: getVal('schOrgSocials')
        };
    }
    if(document.getElementById('schFaqEnable').checked) {
        const items = [];
        document.querySelectorAll('.faq-item').forEach(el => {
            items.push({
                q: el.querySelector('.faq-q').value,
                a: el.querySelector('.faq-a').value
            });
        });
        page.schemas.faq = { items };
    }

    renderPageList();
    alert("Page updated locally. Click 'Save Changes' to push.");
}

function createNewPage() {
    const newPage = { slug: 'new-page', type: 'static', h1: 'New Page', content: '', schemas: {} };
    configData.pages.push(newPage);
    loadPageToEditor(configData.pages.length - 1);
}

function deleteCurrentPage() {
    if(activePageIndex === -1 || configData.pages[activePageIndex].slug === 'home') return;
    if(confirm("Delete?")) {
        configData.pages.splice(activePageIndex, 1);
        activePageIndex = -1;
        document.getElementById('pageEditor').style.display = 'none';
        renderPageList();
    }
}

// ... (saveConfig, helpers, etc. same as before, updated to include new menu arrays) ...
async function saveConfig() {
    const btn = document.getElementById('saveBtn');
    const msg = document.getElementById('statusMsg');
    btn.disabled = true; msg.textContent = "⏳ Uploading...";

    // Save basic settings
    configData.site_settings = {
        title_part_1: getVal('titleP1'), title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'), logo_url: getVal('logoUrl'), favicon: getVal('faviconUrl'),
        ga_id: getVal('gaId'), custom_meta: getVal('customMeta'),
        footer_keywords: getVal('footerKw').split(',').map(s=>s.trim())
    };
    configData.targeting = { country: getVal('tgtCountry'), timezone: getVal('tgtTimezone') };
    configData.wildcard = { category: getVal('wcCategory'), id: getVal('wcId'), fallback: getVal('wcFallback') };
    
    // Save Theme (Including Gradients)
    configData.theme = {
        brand_primary: getVal('colPrimary'), brand_dark: getVal('colDark'), accent_gold: getVal('colGold'),
        status_green: getVal('colStatus'), bg_body: getVal('colBg'),
        hero_gradient_start: getVal('colHeroStart'), trend_gradient_start: getVal('colTrendStart'),
        footer_bg: getVal('colFooter'), font_family: getVal('fontFamily'),
        title_color_1: getVal('colT1'), title_color_2: getVal('colT2'),
        title_italic: document.getElementById('titleItalic').checked
    };
    
    configData.social_stats = {
        telegram: getVal('socTelegram'), twitter: getVal('socTwitter'),
        discord: getVal('socDiscord'), reddit: getVal('socReddit')
    };
    configData.api_keys = { streamed_url: getVal('apiStreamed'), topembed_url: getVal('apiTopembed') };

    // Push to GitHub
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Update Config", content: content, sha: currentSha, branch: BRANCH })
        });
        if(!res.ok) throw new Error((await res.json()).message);
        const data = await res.json();
        currentSha = data.content.sha;
        msg.textContent = "✅ Saved!";
        alert("Saved successfully!");
    } catch (e) { console.error(e); msg.textContent = "❌ Error"; alert(e.message); }
    
    btn.disabled = false;
}

// UI Helpers
function applyTheme(name) {
    const t = THEMES[name]; if(!t) return;
    setColor('colPrimary', 'txtPrimary', t.primary); setColor('colDark', 'txtDark', t.dark);
    setColor('colGold', 'txtGold', t.accent); setColor('colStatus', 'txtStatus', t.status);
    setColor('colBg', 'txtBg', t.bg); setColor('colT1', 'txtT1', t.t1); setColor('colT2', 'txtT2', t.t2);
    updatePreview();
}
function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    // Find active btn
    const btns = document.getElementsByClassName('nav-btn');
    for(let b of btns) { if(b.getAttribute('onclick').includes(id)) b.classList.add('active'); }
}
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id).value; }
function setColor(pid, tid, v) {
    setVal(pid, v); setVal(tid, v);
    const p = document.getElementById(pid); const t = document.getElementById(tid);
    if(p && t) { p.oninput = e => { t.value = e.target.value; updatePreview(); }; t.oninput = e => { p.value = e.target.value; updatePreview(); }; }
}
function saveToken() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); loadConfig(); document.getElementById('authModal').style.display='none'; }
document.getElementById('saveBtn').onclick = saveConfig;
