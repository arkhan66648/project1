const REPO_OWNER = 'arkhan66648'; // YOUR USERNAME
const REPO_NAME = 'project1';     // YOUR REPO
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// --- DEMO DATA (If Config is Missing) ---
const DEMO_CONFIG = {
    site_settings: {
        title_part_1: "Stream", title_part_2: "East", domain: "StreamEast Live",
        logo_url: "",
        custom_meta: "Welcome to the official StreamEast. Watch NBA, NFL, UFC free.",
        ga_id: ""
    },
    theme: {
        brand_primary: "#D00000", brand_dark: "#8a0000", accent_gold: "#FFD700",
        bg_body: "#050505", hero_gradient_start: "#1a0505",
        font_family: "system-ui", title_color_1: "#ffffff", title_color_2: "#D00000"
    },
    sport_priorities: { "NBA": 100, "NFL": 95, "UFC": 90, "MLB": 80 },
    header_menu: [
        { title: "Schedule", url: "#sports" },
        { title: "Features", url: "#features" }
    ],
    hero_categories: [
        { title: "🏀 NBA", url: "#nba" },
        { title: "🏈 NFL", url: "#nfl" }
    ],
    pages: [
        { slug: "home", content: "<h2>Welcome to StreamEast</h2><p>The #1 Source for live sports.</p>" }
    ]
};

let configData = {};
let currentSha = null;
let pollingInterval = null;
let isBuilding = false;

window.addEventListener("DOMContentLoaded", () => {
    // Initialize TinyMCE
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor',
            height: 400,
            skin: 'oxide-dark',
            content_css: 'dark',
            plugins: 'lists link code',
            toolbar: 'undo redo | formatselect | bold italic | alignleft aligncenter | bullist numlist | link code',
            setup: (editor) => {
                editor.on('change', () => {
                    const homePage = configData.pages.find(p => p.slug === 'home');
                    if(homePage) homePage.content = editor.getContent();
                });
            }
        });
    }

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else {
        loadConfig();
        startPolling();
    }
    
    setupInputs();
});

async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        
        if(res.status === 404) {
            console.warn("Config not found. Loading Demo Data.");
            configData = JSON.parse(JSON.stringify(DEMO_CONFIG)); // Deep copy
            populateUI();
            return;
        }

        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        populateUI();
    } catch (e) { console.error("Load Error", e); }
}

function populateUI() {
    const s = configData.site_settings || {};
    const t = configData.theme || {};
    
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('customMeta', s.custom_meta);

    setColor('colPrimary', t.brand_primary);
    
    // Load Content into TinyMCE
    const homePage = configData.pages.find(p => p.slug === 'home');
    if(homePage && tinymce.get('pageContentEditor')) {
        tinymce.get('pageContentEditor').setContent(homePage.content || '');
    }

    renderPriorities();
    renderMenus();
}

function captureAllInputs() {
    configData.site_settings.title_part_1 = getVal('titleP1');
    configData.site_settings.title_part_2 = getVal('titleP2');
    configData.site_settings.domain = getVal('siteDomain');
    configData.site_settings.logo_url = getVal('logoUrl');
    configData.site_settings.custom_meta = getVal('customMeta');
    
    configData.theme.brand_primary = getVal('colPrimary');
    
    // Capture Content
    if(tinymce.get('pageContentEditor')) {
        const content = tinymce.get('pageContentEditor').getContent();
        let homePage = configData.pages.find(p => p.slug === 'home');
        if(!homePage) {
            homePage = { slug: 'home', content: '' };
            configData.pages.push(homePage);
        }
        homePage.content = content;
    }
}

document.getElementById('saveBtn').onclick = async () => {
    if(isBuilding) return;
    updateStatus('building', 'Saving & Triggering Build...');
    document.getElementById('saveBtn').disabled = true;
    captureAllInputs();

    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: "CMS Update via Admin", 
                content: content, 
                sha: currentSha, 
                branch: BRANCH 
            })
        });

        if(res.ok) {
            const data = await res.json();
            currentSha = data.content.sha;
            startPolling(); 
        } else { throw new Error("API Error"); }
    } catch(e) { 
        updateStatus('error', 'Save Failed');
        document.getElementById('saveBtn').disabled = false;
        alert("Check Token / Repo Permissions"); 
    }
};

function startPolling() {
    if(pollingInterval) clearInterval(pollingInterval);
    checkBuildStatus();
    pollingInterval = setInterval(checkBuildStatus, 5000);
}

async function checkBuildStatus() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1`, {
            headers: { 'Authorization': `token ${token}` }
        });
        const data = await res.json();
        
        if(data.workflow_runs && data.workflow_runs.length > 0) {
            const run = data.workflow_runs[0];
            const status = run.status;
            
            if (status === 'queued' || status === 'in_progress') {
                isBuilding = true;
                document.getElementById('saveBtn').disabled = true;
                updateStatus('building', `Building... (${status})`);
            } else if (status === 'completed') {
                isBuilding = false;
                document.getElementById('saveBtn').disabled = false;
                
                if (run.conclusion === 'success') {
                    updateStatus('success', 'Site is Live ✅');
                    clearInterval(pollingInterval);
                } else {
                    updateStatus('error', 'Build Failed ❌');
                    clearInterval(pollingInterval);
                }
            }
        }
    } catch(e) {}
}

function updateStatus(state, text) {
    const box = document.getElementById('buildStatusBox');
    const txt = document.getElementById('buildStatusText');
    box.className = `build-box ${state}`;
    txt.textContent = text;
}
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
function setColor(id, v) { setVal(id, v); }
function setupInputs() { /* Listeners */ }

function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
}
function saveToken() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); location.reload(); }

// --- Priorities ---
function renderPriorities() {
    const container = document.getElementById('priorityListContainer');
    if(!container) return;
    container.innerHTML = '';
    const sorted = Object.entries(configData.sport_priorities || {}).sort((a,b) => b[1] - a[1]);
    
    sorted.forEach(([sport, score]) => {
        const div = document.createElement('div');
        div.className = 'menu-item-row';
        div.innerHTML = `
            <strong>${sport}</strong>
            <div style="display:flex; gap:10px; align-items:center;">
                <input type="number" value="${score}" onchange="updatePriority('${sport}', this.value)" style="width:70px; margin:0;">
                <button class="btn-x" onclick="deletePriority('${sport}')">×</button>
            </div>
        `;
        container.appendChild(div);
    });
}
window.updatePriority = (sport, val) => { configData.sport_priorities[sport] = parseInt(val); };
window.deletePriority = (sport) => { delete configData.sport_priorities[sport]; renderPriorities(); };
window.addPriorityRow = () => {
    const name = getVal('newSportName');
    if(name) {
        if(!configData.sport_priorities) configData.sport_priorities = {};
        configData.sport_priorities[name] = 50;
        setVal('newSportName', '');
        renderPriorities();
    }
};

// --- Menus ---
function renderMenus() {
    renderMenuSection('header', configData.header_menu);
    renderMenuSection('hero', configData.hero_categories);
}
function renderMenuSection(id, items) {
    const cont = document.getElementById(`menu-${id}`);
    if(!cont) return;
    cont.innerHTML = (items || []).map((item, idx) => `
        <div class="menu-item-row">
            <div><strong>${item.title}</strong><br><small>${item.url}</small></div>
            <button class="btn-x" onclick="deleteMenuItem('${id}', ${idx})">×</button>
        </div>
    `).join('');
}
window.openMenuModal = (sec) => {
    document.getElementById('menuTargetSection').value = sec;
    setVal('menuTitleItem', ''); setVal('menuUrlItem', '');
    document.getElementById('menuModal').style.display = 'flex';
}
window.saveMenuItem = () => {
    const sec = document.getElementById('menuTargetSection').value;
    const item = { title: getVal('menuTitleItem'), url: getVal('menuUrlItem') };
    if(!item.title || !item.url) return;
    
    if(sec === 'header') configData.header_menu.push(item);
    if(sec === 'hero') configData.hero_categories.push(item);
    
    renderMenus();
    document.getElementById('menuModal').style.display = 'none';
}
window.deleteMenuItem = (sec, idx) => {
    if(sec === 'header') configData.header_menu.splice(idx, 1);
    if(sec === 'hero') configData.hero_categories.splice(idx, 1);
    renderMenus();
}
