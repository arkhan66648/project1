// ==========================================
// CONFIGURATION
// ==========================================
const REPO_OWNER = 'arkhan66648'; // UPDATE THIS
const REPO_NAME = 'project1';       // UPDATE THIS
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// DEFAULT THEME (For Reset Button)
const DEFAULT_THEME = {
    brand_primary: "#D00000",
    brand_dark: "#8a0000",
    accent_gold: "#FFD700",
    bg_body: "#050505",
    font_family: "system-ui"
};

let currentSha = null;
let configData = {};

document.addEventListener("DOMContentLoaded", () => {
    tinymce.init({
        selector: '#tinymce-editor',
        height: 500,
        skin: "oxide-dark",
        content_css: "dark",
        plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount',
        toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline | link image media table | align'
    });

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();

    // Font Preview Listener
    document.getElementById('fontFamily').addEventListener('change', (e) => {
        document.getElementById('fontPreview').style.fontFamily = e.target.value;
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
    setVal('metaTitle', s.meta_title);
    setVal('metaDesc', s.meta_desc);
    setVal('apiStreamed', api.streamed_url);
    setVal('apiTopembed', api.topembed_url);
    setVal('footerKeywords', (s.footer_keywords || []).join(', '));

    // Appearance
    setColor('colPrimary', 'txtPrimary', t.brand_primary || DEFAULT_THEME.brand_primary);
    setColor('colDark', 'txtDark', t.brand_dark || DEFAULT_THEME.brand_dark);
    setColor('colGold', 'txtGold', t.accent_gold || DEFAULT_THEME.accent_gold);
    setColor('colBg', 'txtBg', t.bg_body || DEFAULT_THEME.bg_body);
    setVal('fontFamily', t.font_family || DEFAULT_THEME.font_family);

    // Socials
    setVal('socTelegram', soc.telegram);
    setVal('socTwitter', soc.twitter);
    setVal('socDiscord', soc.discord);
    setVal('socReddit', soc.reddit);

    // Lists (Hero & Header)
    const hContainer = document.getElementById('hero-container');
    hContainer.innerHTML = '';
    (data.hero_categories || []).forEach(item => addHeroUI(item));

    const mContainer = document.getElementById('header-container');
    mContainer.innerHTML = '';
    (data.header_menu || []).forEach(item => addHeaderUI(item));
}

// ==========================================
// SAVING
// ==========================================
async function saveConfig() {
    const btn = document.getElementById('saveBtn');
    btn.textContent = "Saving..."; btn.disabled = true;

    // Construct Data Object
    configData.site_settings = {
        title_part_1: getVal('titleP1'),
        title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        meta_title: getVal('metaTitle'),
        meta_desc: getVal('metaDesc'),
        footer_keywords: getVal('footerKeywords').split(',').map(s => s.trim())
    };

    configData.theme = {
        brand_primary: getVal('colPrimary'),
        brand_dark: getVal('colDark'),
        accent_gold: getVal('colGold'),
        bg_body: getVal('colBg'),
        font_family: getVal('fontFamily')
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

    // Arrays
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

    // Github Put Request
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Admin Update", content: content, sha: currentSha, branch: BRANCH })
        });
        const data = await res.json();
        currentSha = data.content.sha;
        alert("Saved! Site will update in ~2 mins.");
    } catch (e) { alert("Error saving."); }
    btn.textContent = "💾 Save Changes"; btn.disabled = false;
}

// ==========================================
// UI MANAGERS
// ==========================================
function addHeroUI(data = {title:'', folder:''}) {
    const div = document.createElement('div');
    div.className = 'hero-item sitelink-item';
    div.innerHTML = `
        <div style="display:flex; gap:10px;">
            <input type="text" class="h-title" placeholder="Name (e.g. 🏀 NBA)" value="${data.title}">
            <input type="text" class="h-folder" placeholder="Folder (e.g. nba)" value="${data.folder}">
            <button class="btn-delete" onclick="this.parentElement.parentElement.remove()">✕</button>
        </div>`;
    document.getElementById('hero-container').appendChild(div);
}

function addHeaderUI(data = {title:'', url:''}) {
    const div = document.createElement('div');
    div.className = 'menu-item sitelink-item';
    div.innerHTML = `
        <div style="display:flex; gap:10px;">
            <input type="text" class="m-title" placeholder="Link Name" value="${data.title}">
            <input type="text" class="m-url" placeholder="URL (#id or https://)" value="${data.url}">
            <button class="btn-delete" onclick="this.parentElement.parentElement.remove()">✕</button>
        </div>`;
    document.getElementById('header-container').appendChild(div);
}

function resetTheme() {
    if(confirm("Reset all colors to default?")) {
        setColor('colPrimary', 'txtPrimary', DEFAULT_THEME.brand_primary);
        setColor('colDark', 'txtDark', DEFAULT_THEME.brand_dark);
        setColor('colGold', 'txtGold', DEFAULT_THEME.accent_gold);
        setColor('colBg', 'txtBg', DEFAULT_THEME.bg_body);
        setVal('fontFamily', DEFAULT_THEME.font_family);
    }
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
