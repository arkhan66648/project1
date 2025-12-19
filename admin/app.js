const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';       
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// Categories for Dropdowns (Matches Python)
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

document.addEventListener("DOMContentLoaded", () => {
    // Sidebar Toggle
    document.getElementById('sidebarToggle').onclick = () => 
        document.getElementById('sidebar').classList.toggle('minimized');

    // Populate Dropdowns
    const wcSelect = document.getElementById('wcCategory');
    const pCatAssign = document.getElementById('pCategoryAssign');
    CATEGORIES.forEach(cat => {
        wcSelect.innerHTML += `<option value="${cat}">${cat}</option>`;
        pCatAssign.innerHTML += `<option value="${cat}">${cat}</option>`;
    });

    // Init Editor
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#tinymce-editor',
            height: 450,
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

    // Input Listeners for Live Updates in Page Editor
    ['pSlug', 'pH1', 'pType'].forEach(id => {
        document.getElementById(id).addEventListener('input', () => {
            if(activePageIndex > -1) {
                const p = configData.pages[activePageIndex];
                if(id === 'pSlug' && p.slug !== 'home') p.slug = document.getElementById(id).value;
                if(id === 'pH1') p.h1 = document.getElementById(id).value;
                if(id === 'pType') p.type = document.getElementById(id).value;
                renderPageList(); // Refresh list to show changes
            }
        });
    });

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();
});

// ==========================================
// CORE FUNCTIONS
// ==========================================
async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    document.getElementById('statusMsg').textContent = "⏳ Loading...";
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        if (res.status === 404) { initNewConfig(); return; }
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
    if(!configData.social_stats) configData.social_stats = {};
    if(!configData.targeting) configData.targeting = { country: 'USA', timezone: 'US/Eastern' };
}

function populateUI() {
    const s = configData.site_settings || {};
    const t = configData.theme || {};
    const soc = configData.social_stats || {};
    const wc = configData.wildcard || {};

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
    
    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    renderPageList();
    renderMenus();
}

// ==========================================
// PAGE MANAGER
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
}

function createNewPage() {
    const newPage = { slug: 'new-page-' + Date.now(), h1: 'New Page', type: 'static', content: '' };
    configData.pages.push(newPage);
    loadPage(configData.pages.length - 1);
}

// CRITICAL: Deletes file from GitHub + Removes from Config
async function deleteCurrentPage() {
    if(activePageIndex === -1) return;
    const p = configData.pages[activePageIndex];
    if(p.slug === 'home') return;

    if(!confirm(`Delete page /${p.slug} permanently? This deletes the folder from GitHub.`)) return;

    const token = localStorage.getItem('gh_token');
    
    // 1. Try to delete the file on GitHub
    // We try to delete slug/index.html
    const path = `${p.slug}/index.html`;
    try {
        // Get SHA of the file first
        const getRes = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        
        if(getRes.ok) {
            const fileData = await getRes.json();
            const delRes = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}`, {
                method: 'DELETE',
                headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `Deleted page: ${p.slug}`,
                    sha: fileData.sha,
                    branch: BRANCH
                })
            });
            if(!delRes.ok) console.warn("Failed to delete file on GitHub (might not exist)");
        }
    } catch(e) { console.error("Deletion API error", e); }

    // 2. Remove from Config
    configData.pages.splice(activePageIndex, 1);
    activePageIndex = -1;
    document.getElementById('pageEditor').style.display = 'none';
    renderPageList();
    alert("Page deleted. Don't forget to save changes!");
}

function saveCurrentPageLocal() {
    if(activePageIndex === -1) return;
    const p = configData.pages[activePageIndex];
    if(p.slug !== 'home') p.slug = getVal('pSlug');
    p.type = getVal('pType');
    p.assigned_category = getVal('pCategoryAssign');
    p.h1 = getVal('pH1');
    p.hero_text = getVal('pHero');
    p.meta_title = getVal('pMetaTitle');
    p.meta_desc = getVal('pMetaDesc');
    if(tinymce.get('tinymce-editor')) p.content = tinymce.get('tinymce-editor').getContent();
    
    renderPageList();
    alert("Page Saved Locally. Click 'Save All Changes' to Publish.");
}

// ==========================================
// SAVING
// ==========================================
async function saveConfig() {
    const btn = document.getElementById('saveBtn');
    btn.disabled = true; document.getElementById('statusMsg').textContent = "Uploading...";

    // Capture Inputs
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

    // Push Config
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Update Config", content: content, sha: currentSha, branch: BRANCH })
        });
        const d = await res.json();
        currentSha = d.content.sha;
        document.getElementById('statusMsg').textContent = "✅ Saved!";
    } catch(e) { alert("Error: " + e.message); }
    btn.disabled = false;
}

// Helpers
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
function setColor(pid, tid, v) { setVal(pid, v); setVal(tid, v); }
function saveToken() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); loadConfig(); document.getElementById('authModal').style.display='none'; }
function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
}
document.getElementById('saveBtn').onclick = saveConfig;

// Menus Render Logic (Simplified for brevity - assumes you have the modal logic from prev step)
function renderMenus() {
    ['header', 'hero', 'footer_league', 'footer_static'].forEach(k => {
        const cont = document.getElementById(`menu-${k.replace('_','-')}`);
        if(cont && configData[k + '_menu'] || configData[k + '_categories']) {
            const arr = configData[k + '_menu'] || configData[k + '_categories'] || [];
            cont.innerHTML = arr.map((item, idx) => `
                <div class="menu-list-item">
                    <span>${item.title}</span>
                    <button class="btn-del-mini" onclick="delMenu('${k}', ${idx})">×</button>
                </div>
            `).join('');
        }
    });
}
function delMenu(key, idx) {
    const arrKey = key.includes('hero') ? 'hero_categories' : key + '_menu';
    configData[arrKey].splice(idx, 1);
    renderMenus();
}
