// ==========================================
// CONFIG: UPDATE THESE TWO LINES!
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';       
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// CATEGORIES FOR WILDCARD DROPDOWN (Matches Python)
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
    targeting: {}, // New object
    wildcard: {},  // New object
    social_stats: {}, 
    api_keys: {}, 
    hero_categories: [], 
    header_menu: []
};
let activePageIndex = -1;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Sidebar Toggle Logic
    const toggle = document.getElementById('sidebarToggle');
    toggle.addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('minimized');
    });

    // 2. Populate Wildcard Dropdown
    const wcSelect = document.getElementById('wcCategory');
    CATEGORIES.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.innerText = cat;
        wcSelect.appendChild(opt);
    });

    // 3. Init Editor
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#tinymce-editor',
            height: 400,
            skin: "oxide-dark",
            content_css: "dark",
            plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount code',
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline | link image media table | align | code',
            setup: (editor) => { editor.on('change', () => { if(activePageIndex > -1) configData.pages[activePageIndex].content = editor.getContent(); }); }
        });
    }

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();

    // Live Font Preview listeners
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
    if(document.getElementById('titleItalic').checked) prev.style.fontStyle = 'italic'; else prev.style.fontStyle = 'normal';
}

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
        
        // Ensure structure exists
        if(!configData.pages) configData.pages = [];
        if(!configData.targeting) configData.targeting = { country: 'USA', timezone: 'US/Eastern' };
        if(!configData.wildcard) configData.wildcard = { category: '', id: '', fallback: '' };

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
    const soc = data.social_stats || {};
    const api = data.api_keys || {};
    const tgt = data.targeting || {};
    const wc = data.wildcard || {};

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

    // Targeting & Wildcard
    setVal('tgtCountry', tgt.country || 'USA');
    setVal('tgtTimezone', tgt.timezone || 'US/Eastern');
    setVal('wcCategory', wc.category);
    setVal('wcId', wc.id);
    setVal('wcFallback', wc.fallback);
    
    // Update Priority Strategy Text
    const strategy = tgt.country === 'UK' ? "UK Focused (Soccer/Boxing)" : "USA Focused (NFL/NBA)";
    document.getElementById('currentStrategy').innerText = strategy;

    // Appearance (Including New Gradients)
    setColor('colPrimary', 'txtPrimary', t.brand_primary || '#D00000');
    setColor('colDark', 'txtDark', t.brand_dark || '#8a0000');
    setColor('colGold', 'txtGold', t.accent_gold || '#FFD700');
    setColor('colStatus', 'txtStatus', t.status_green || '#00e676');
    setColor('colBg', 'txtBg', t.bg_body || '#050505');
    
    // New Color Fields
    setColor('colHeroStart', 'txtHeroStart', t.hero_gradient_start || '#1a0505');
    setColor('colTrendStart', 'txtTrendStart', t.trend_gradient_start || '#140000');
    setColor('colFooter', 'txtFooter', t.footer_bg || '#000000');

    setVal('fontFamily', t.font_family || 'system-ui');
    setColor('colT1', 'txtT1', t.title_color_1 || '#ffffff');
    setColor('colT2', 'txtT2', t.title_color_2 || '#D00000');
    if(document.getElementById('titleItalic')) document.getElementById('titleItalic').checked = t.title_italic || false;

    // Socials
    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    // Menus
    const hContainer = document.getElementById('hero-container');
    if(hContainer) {
        hContainer.innerHTML = '';
        (data.hero_categories || []).forEach(item => addHeroUI(item));
    }

    const mContainer = document.getElementById('header-container');
    if(mContainer) {
        mContainer.innerHTML = '';
        (data.header_menu || []).forEach(item => addHeaderUI(item));
    }

    // Pages
    renderPageList();
    updatePreview();
}

// ... (Page Manager Code remains mostly same until Step 2, but ensuring functionality)
function renderPageList() {
    const list = document.getElementById('pagesList');
    if(!list) return;
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
    
    // Disable slug edit for home
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
    setVal('pH1', page.h1);
    setVal('pHero', page.hero_text);
    setVal('pMetaTitle', page.meta_title);
    setVal('pMetaDesc', page.meta_desc);
    
    if(tinymce.get('tinymce-editor')) tinymce.get('tinymce-editor').setContent(page.content || '');
}

function saveCurrentPageLocal() {
    if(activePageIndex === -1) return;
    const page = configData.pages[activePageIndex];
    
    if(page.slug !== 'home') page.slug = getVal('pSlug');
    page.type = getVal('pType');
    page.h1 = getVal('pH1');
    page.title = getVal('pH1'); 
    page.hero_text = getVal('pHero');
    page.meta_title = getVal('pMetaTitle');
    page.meta_desc = getVal('pMetaDesc');
    if(tinymce.get('tinymce-editor')) page.content = tinymce.get('tinymce-editor').getContent();
    
    renderPageList();
    alert("Page updated locally. Click 'Save Changes' to push to GitHub.");
}

function createNewPage() {
    const newPage = { slug: 'new-page', type: 'static', h1: 'New Page', content: '' };
    configData.pages.push(newPage);
    loadPageToEditor(configData.pages.length - 1);
}

function deleteCurrentPage() {
    if(activePageIndex === -1) return;
    if(configData.pages[activePageIndex].slug === 'home') { alert("Cannot delete Home."); return; }
    
    if(confirm("Delete this page?")) {
        configData.pages.splice(activePageIndex, 1);
        activePageIndex = -1;
        document.getElementById('pageEditor').style.display = 'none';
        renderPageList();
    }
}

async function saveConfig() {
    const btn = document.getElementById('saveBtn');
    const msg = document.getElementById('statusMsg');
    btn.disabled = true;
    msg.textContent = "⏳ Uploading...";

    // 1. Gather Data
    configData.site_settings = {
        title_part_1: getVal('titleP1'),
        title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        favicon: getVal('faviconUrl'),
        ga_id: getVal('gaId'),
        custom_meta: getVal('customMeta'),
        footer_keywords: getVal('footerKw').split(',').map(s=>s.trim())
    };

    configData.targeting = {
        country: getVal('tgtCountry'),
        timezone: getVal('tgtTimezone')
    };

    configData.wildcard = {
        category: getVal('wcCategory'),
        id: getVal('wcId'),
        fallback: getVal('wcFallback')
    };

    configData.theme = {
        brand_primary: getVal('colPrimary'),
        brand_dark: getVal('colDark'),
        accent_gold: getVal('colGold'),
        status_green: getVal('colStatus'),
        bg_body: getVal('colBg'),
        hero_gradient_start: getVal('colHeroStart'), // New
        trend_gradient_start: getVal('colTrendStart'), // New
        footer_bg: getVal('colFooter'), // New
        font_family: getVal('fontFamily'),
        title_color_1: getVal('colT1'),
        title_color_2: getVal('colT2'),
        title_italic: document.getElementById('titleItalic').checked
    };

    configData.social_stats = {
        telegram: getVal('socTelegram'),
        twitter: getVal('socTwitter'),
        discord: getVal('socDiscord'),
        reddit: getVal('socReddit')
    };

    configData.api_keys = {
        streamed_url: getVal('apiStreamed'),
        topembed_url: getVal('apiTopembed')
    };

    // Arrays (Menus - Simple version for Step 1, will upgrade in Step 2)
    configData.hero_categories = [];
    document.querySelectorAll('.hero-item').forEach(el => {
        configData.hero_categories.push({
            title: el.querySelector('.h-title').value,
            folder: el.querySelector('.h-folder').value
        });
    });

    configData.header_menu = [];
    document.querySelectorAll('.menu-item').forEach(el => {
        configData.header_menu.push({
            title: el.querySelector('.m-title').value,
            url: el.querySelector('.m-url').value
        });
    });

    // 2. Push to GitHub
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    const payload = {
        message: "Admin Panel: Config Update",
        content: content,
        branch: BRANCH
    };
    if(currentSha) payload.sha = currentSha;

    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if(!res.ok) throw new Error((await res.json()).message);

        const data = await res.json();
        currentSha = data.content.sha;
        msg.textContent = "✅ Saved!";
        alert("Configuration saved!");
        
    } catch (e) { 
        console.error(e); 
        msg.textContent = "❌ Error";
        alert("Error: " + e.message); 
    }
    
    btn.disabled = false;
}

// UI Helpers
function applyTheme(name) {
    const t = THEMES[name];
    if(!t) return;
    setColor('colPrimary', 'txtPrimary', t.primary);
    setColor('colDark', 'txtDark', t.dark);
    setColor('colGold', 'txtGold', t.accent);
    setColor('colStatus', 'txtStatus', t.status);
    setColor('colBg', 'txtBg', t.bg);
    setColor('colT1', 'txtT1', t.t1);
    setColor('colT2', 'txtT2', t.t2);
    updatePreview();
}

function addHeroUI(data = {title:'', folder:''}) {
    const div = document.createElement('div');
    div.className = 'hero-item sitelink-item';
    div.innerHTML = `
        <input type="text" class="h-title" placeholder="Name" value="${data.title}">
        <input type="text" class="h-folder" placeholder="Folder" value="${data.folder}">
        <button class="btn-delete" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('hero-container').appendChild(div);
}

function addHeaderUI(data = {title:'', url:''}) {
    const div = document.createElement('div');
    div.className = 'menu-item sitelink-item';
    div.innerHTML = `
        <input type="text" class="m-title" placeholder="Name" value="${data.title}">
        <input type="text" class="m-url" placeholder="URL" value="${data.url}">
        <button class="btn-delete" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('header-container').appendChild(div);
}

function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    // Find button that calls this
    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.getAttribute('onclick').includes(id));
    if(btn) btn.classList.add('active');
}

function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id).value; }

function setColor(pid, tid, v) {
    setVal(pid, v); setVal(tid, v);
    const p = document.getElementById(pid);
    const t = document.getElementById(tid);
    if(p && t) {
        p.oninput = e => { t.value = e.target.value; updatePreview(); };
        t.oninput = e => { p.value = e.target.value; updatePreview(); };
    }
}

function saveToken() { 
    localStorage.setItem('gh_token', document.getElementById('ghToken').value); 
    loadConfig(); 
    document.getElementById('authModal').style.display='none'; 
}

document.getElementById('saveBtn').onclick = saveConfig;
