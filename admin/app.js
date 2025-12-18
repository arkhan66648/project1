// ==========================================
// CONFIG: UPDATE THESE!
// ==========================================
const REPO_OWNER = 'YOUR_GITHUB_USERNAME'; // UPDATE THIS
const REPO_NAME = 'YOUR_REPO_NAME';       // UPDATE THIS
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// THEME PRESETS
const THEMES = {
    red: { primary: "#D00000", dark: "#8a0000", accent: "#FFD700", status: "#00e676", bg: "#050505", t1: "#ffffff", t2: "#D00000" },
    blue: { primary: "#0056D2", dark: "#003c96", accent: "#00C2CB", status: "#00e676", bg: "#050505", t1: "#ffffff", t2: "#0056D2" },
    green: { primary: "#008f39", dark: "#006428", accent: "#BBF7D0", status: "#22c55e", bg: "#050505", t1: "#ffffff", t2: "#008f39" },
    purple: { primary: "#7C3AED", dark: "#5B21B6", accent: "#F472B6", status: "#34d399", bg: "#050505", t1: "#ffffff", t2: "#7C3AED" }
};

let currentSha = null;
let configData = {};
let activePageIndex = -1;

document.addEventListener("DOMContentLoaded", () => {
    tinymce.init({
        selector: '#tinymce-editor',
        height: 400,
        skin: "oxide-dark",
        content_css: "dark",
        plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount',
        toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline | link image media table | align',
        setup: (editor) => { editor.on('change', () => { if(activePageIndex > -1) configData.pages[activePageIndex].content = editor.getContent(); }); }
    });

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();

    // Live Font Preview
    const updatePreview = () => {
        const prev = document.getElementById('fontPreview');
        prev.style.fontFamily = getVal('fontFamily');
        prev.innerHTML = `<span style="color:${getVal('colT1')}">${getVal('titleP1') || 'Stream'}</span><span style="color:${getVal('colT2')}">${getVal('titleP2') || 'East'}</span>`;
        if(document.getElementById('titleItalic').checked) prev.style.fontStyle = 'italic'; else prev.style.fontStyle = 'normal';
    };
    ['fontFamily','titleP1','titleP2','colT1','colT2','titleItalic'].forEach(id => {
        document.getElementById(id).addEventListener('input', updatePreview);
    });
});

// ==========================================
// DATA LOADING
// ==========================================
async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        
        // Ensure pages array exists
        if(!configData.pages) configData.pages = [{slug: 'home', type:'schedule', h1:'Home', content:''}];
        
        populateUI(configData);
    } catch (err) { console.error(err); alert("Failed to load config."); }
}

function populateUI(data) {
    const s = data.site_settings || {};
    const t = data.theme || {};
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

    // Appearance
    setColor('colPrimary', 'txtPrimary', t.brand_primary || '#D00000');
    setColor('colDark', 'txtDark', t.brand_dark || '#8a0000');
    setColor('colGold', 'txtGold', t.accent_gold || '#FFD700');
    setColor('colStatus', 'txtStatus', t.status_green || '#00e676');
    setColor('colBg', 'txtBg', t.bg_body || '#050505');
    setVal('fontFamily', t.font_family || 'system-ui');
    
    setColor('colT1', 'txtT1', t.title_color_1 || '#ffffff');
    setColor('colT2', 'txtT2', t.title_color_2 || '#D00000');
    document.getElementById('titleItalic').checked = t.title_italic || false;

    // Socials
    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    // Menus
    const hContainer = document.getElementById('hero-container');
    hContainer.innerHTML = '';
    (data.hero_categories || []).forEach(item => addHeroUI(item));

    const mContainer = document.getElementById('header-container');
    mContainer.innerHTML = '';
    (data.header_menu || []).forEach(item => addHeaderUI(item));

    // Pages
    renderPageList();
}

// ==========================================
// PAGE MANAGER (Major Feature)
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
    renderPageList(); // Update active class
    
    document.getElementById('pageEditor').style.display = 'flex';
    document.getElementById('editHeading').innerText = `Editing: ${page.slug}`;
    document.getElementById('btnDeletePage').style.display = page.slug === 'home' ? 'none' : 'block';

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
    
    page.slug = getVal('pSlug');
    page.type = getVal('pType');
    page.h1 = getVal('pH1');
    page.title = getVal('pH1'); // Fallback title
    page.hero_text = getVal('pHero');
    page.meta_title = getVal('pMetaTitle');
    page.meta_desc = getVal('pMetaDesc');
    page.content = tinymce.get('tinymce-editor').getContent();
    
    renderPageList();
    alert("Page updated locally. Click 'Save All Changes' to publish.");
}

function createNewPage() {
    const newPage = { slug: 'new-page', type: 'static', h1: 'New Page', content: '' };
    configData.pages.push(newPage);
    loadPageToEditor(configData.pages.length - 1);
}

function deleteCurrentPage() {
    if(confirm("Delete this page?")) {
        configData.pages.splice(activePageIndex, 1);
        activePageIndex = -1;
        document.getElementById('pageEditor').style.display = 'none';
        renderPageList();
    }
}

// ==========================================
// SAVING GLOBAL CONFIG
// ==========================================
async function saveConfig() {
    const btn = document.getElementById('saveBtn');
    btn.textContent = "Saving..."; btn.disabled = true;

    // Gather General Settings
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

    // Gather Theme (Excluding Content)
    configData.theme = {
        brand_primary: getVal('colPrimary'),
        brand_dark: getVal('colDark'),
        accent_gold: getVal('colGold'),
        status_green: getVal('colStatus'),
        bg_body: getVal('colBg'),
        font_family: getVal('fontFamily'),
        title_color_1: getVal('colT1'),
        title_color_2: getVal('colT2'),
        title_italic: document.getElementById('titleItalic').checked
    };

    // Gather Socials
    configData.social_stats = {
        telegram: getVal('socTelegram'),
        twitter: getVal('socTwitter'),
        discord: getVal('socDiscord'),
        reddit: getVal('socReddit')
    };

    // Gather APIs
    configData.api_keys = {
        streamed_url: getVal('apiStreamed'),
        topembed_url: getVal('apiTopembed')
    };

    // Gather Menus
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
    
    // IMPORTANT: configData.pages is already updated by saveCurrentPageLocal()
    // We just need to ensure it's part of the object we send (it is, because we modify configData directly)

    // Send to GitHub
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Admin: Full Config Update", content: content, sha: currentSha, branch: BRANCH })
        });
        const data = await res.json();
        currentSha = data.content.sha;
        alert("Saved! Site update triggered.");
    } catch (e) { console.error(e); alert("Save Error."); }
    btn.textContent = "💾 Save All Changes"; btn.disabled = false;
}

// ==========================================
// UI MANAGERS
// ==========================================
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
}

function addHeroUI(data = {title:'', folder:''}) {
    const div = document.createElement('div');
    div.className = 'hero-item sitelink-item';
    div.innerHTML = `<input type="text" class="h-title" placeholder="Name" value="${data.title}">
                     <input type="text" class="h-folder" placeholder="Folder" value="${data.folder}">
                     <button class="btn-delete" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('hero-container').appendChild(div);
}

function addHeaderUI(data = {title:'', url:''}) {
    const div = document.createElement('div');
    div.className = 'menu-item sitelink-item';
    div.innerHTML = `<input type="text" class="m-title" placeholder="Link Name" value="${data.title}">
                     <input type="text" class="m-url" placeholder="URL" value="${data.url}">
                     <button class="btn-delete" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('header-container').appendChild(div);
}

// Helpers
function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.target.classList.add('active');
}
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id).value; }
function setColor(pid, tid, v) {
    setVal(pid, v); setVal(tid, v);
    document.getElementById(pid).oninput = e => document.getElementById(tid).value = e.target.value;
    document.getElementById(tid).oninput = e => document.getElementById(pid).value = e.target.value;
}
function saveToken() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); loadConfig(); document.getElementById('authModal').style.display='none'; }
document.getElementById('saveBtn').onclick = saveConfig;
