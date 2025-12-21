// ==========================================
// 1. CONFIGURATION (YOU MUST EDIT THIS)
// ==========================================
// Your GitHub Username (e.g., 'john-doe')
const REPO_OWNER = 'arkhan66648'; 

// Your Repository Name (e.g., 'sports-site')
const REPO_NAME = 'project1';     

const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// ==========================================
// 2. DEMO DATA (Fallback)
// ==========================================
const DEMO_CONFIG = {
    site_settings: {
        title_part_1: "Stream", title_part_2: "East", domain: "StreamEast Live",
        logo_url: "assets/streameast-logo-hd.jpg",
        custom_meta: "Welcome to the official StreamEast. Watch NBA, NFL, UFC free.",
        ga_id: "", target_country: "US"
    },
    theme: {
        brand_primary: "#D00000", brand_dark: "#8a0000", accent_gold: "#FFD700",
        bg_body: "#050505", hero_gradient_start: "#1a0505",
        font_family: "system-ui", title_color_1: "#ffffff", title_color_2: "#D00000"
    },
    sport_priorities: { 
        US: { "NFL": 100, "NBA": 95, "UFC": 90, "MLB": 80 },
        UK: { "Premier League": 100, "Cricket": 95, "F1": 90 }
    },
    header_menu: [
        { title: "Schedule", url: "#sports" },
        { title: "Features", url: "#features" }
    ],
    hero_categories: [
        { title: "🏀 NBA", url: "/nba/" },
        { title: "🏈 NFL", url: "/nfl/" }
    ],
    pages: [
        { slug: "home", content: "<h2>Welcome to StreamEast</h2><p>The #1 Source for live sports.</p>" }
    ]
};

let configData = {};
let currentSha = null;
let pollingInterval = null;
let isBuilding = false;

// ==========================================
// 3. INITIALIZATION & AUTH
// ==========================================
window.addEventListener("DOMContentLoaded", () => {
    // Init TinyMCE
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { 
                ed.on('change', () => { 
                    const p = configData.pages?.find(x => x.slug === 'home');
                    if(p) p.content = ed.getContent();
                });
            }
        });
    }

    // Check Auth
    const token = localStorage.getItem('gh_token');
    if (!token) {
        showLoginModal();
    } else {
        verifyAndLoad(token);
    }

    // Input Listeners
    setupInputs();
});

function showLoginModal() {
    document.getElementById('authModal').style.display = 'flex';
    // Clear any existing value
    document.getElementById('ghToken').value = ''; 
    document.getElementById('ghToken').focus();
}

// CALLED BY LOGIN BUTTON
window.saveToken = async () => {
    const token = document.getElementById('ghToken').value.trim();
    if(!token) return alert("Please enter a GitHub Token");
    
    const btn = document.querySelector('#authModal .save-btn');
    const originalText = btn.innerText;
    btn.innerText = "Verifying...";
    btn.disabled = true;

    try {
        // FIXED: Using 'token' prefix instead of 'Bearer' for maximum compatibility
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}`, {
            headers: { 
                'Authorization': `token ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });

        if (res.status === 200) {
            localStorage.setItem('gh_token', token);
            document.getElementById('authModal').style.display = 'none';
            verifyAndLoad(token);
        } else if (res.status === 404) {
            alert(`Error 404: Repository "${REPO_OWNER}/${REPO_NAME}" not found.\n\nDid you update REPO_OWNER in admin/app.js?`);
        } else if (res.status === 401) {
            alert("Error 401: Invalid Token. Check your permissions.");
        } else {
            alert(`Connection Error (${res.status}): ${res.statusText}`);
        }
    } catch(e) {
        console.error(e);
        alert("Network Error: Check console for details.");
    }

    btn.innerText = originalText;
    btn.disabled = false;
};

// LOAD DATA
async function verifyAndLoad(token) {
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });

        if (res.status === 401) {
            localStorage.removeItem('gh_token');
            showLoginModal();
            return;
        }

        // Handle missing config (First run)
        if (res.status === 404) {
            console.warn("Config not found. Initializing Demo Data.");
            configData = JSON.parse(JSON.stringify(DEMO_CONFIG));
            populateUI();
            return;
        }

        const data = await res.json();
        currentSha = data.sha;
        
        // Robust Decoding
        try {
            const decoded = decodeURIComponent(escape(atob(data.content)));
            configData = JSON.parse(decoded);
        } catch(err) {
            console.error("JSON Parse Error", err);
            configData = JSON.parse(JSON.stringify(DEMO_CONFIG)); // Fallback
        }
        
        populateUI();
        startPolling(); 

    } catch (e) {
        console.error("Critical Load Error", e);
        // Don't alert here to avoid loop, just log
    }
}

// ==========================================
// 4. UI LOGIC (Populate & Capture)
// ==========================================
function populateUI() {
    if(!configData.site_settings) configData.site_settings = {};
    if(!configData.theme) configData.theme = {};
    if(!configData.sport_priorities) configData.sport_priorities = { US: {}, UK: {} };

    const s = configData.site_settings;
    const t = configData.theme;
    
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('customMeta', s.custom_meta);
    setVal('targetCountry', s.target_country || 'US');

    // Content Editor
    const home = configData.pages?.find(p => p.slug === 'home');
    if(home && tinymce.get('pageContentEditor')) {
        tinymce.get('pageContentEditor').setContent(home.content || '');
    }

    renderPriorities();
    renderMenus();
}

function captureAllInputs() {
    const country = getVal('targetCountry');
    
    configData.site_settings = {
        title_part_1: getVal('titleP1'),
        title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        custom_meta: getVal('customMeta'),
        target_country: country
    };
    
    // Capture Page Content
    if(tinymce.get('pageContentEditor')) {
        const content = tinymce.get('pageContentEditor').getContent();
        if(!configData.pages) configData.pages = [];
        let p = configData.pages.find(x => x.slug === 'home');
        if(!p) { p = { slug: 'home' }; configData.pages.push(p); }
        p.content = content;
    }
}

// ==========================================
// 5. PRIORITIES & MENUS
// ==========================================
function renderPriorities() {
    const country = getVal('targetCountry') || 'US';
    const container = document.getElementById('priorityListContainer');
    if(!container) return;
    
    const lbl = document.getElementById('prioLabel');
    if(lbl) lbl.innerText = country;

    if (!configData.sport_priorities[country]) configData.sport_priorities[country] = {};

    container.innerHTML = '';
    
    // Sort by score (descending)
    const items = Object.entries(configData.sport_priorities[country])
        .map(([name, data]) => {
            // Support legacy format (just number) or new object format
            if (typeof data === 'number') return { name, score: data, isLeague: false, hasLink: false };
            return { name, ...data };
        })
        .sort((a,b) => b.score - a.score);
    
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'menu-item-row';
        div.style.flexWrap = "wrap";
        div.innerHTML = `
            <strong style="width:150px; overflow:hidden;">${item.name}</strong>
            <div style="display:flex; gap:15px; align-items:center; flex:1;">
                <label style="margin:0; font-size:0.8rem; display:flex; align-items:center; gap:5px;">
                    <input type="checkbox" ${item.isLeague ? 'checked' : ''} 
                           onchange="updatePriorityMeta('${country}', '${item.name}', 'isLeague', this.checked)">
                    Is League?
                </label>
                <label style="margin:0; font-size:0.8rem; display:flex; align-items:center; gap:5px;">
                    <input type="checkbox" ${item.hasLink ? 'checked' : ''} 
                           onchange="updatePriorityMeta('${country}', '${item.name}', 'hasLink', this.checked)">
                    Add Link?
                </label>
                <input type="number" value="${item.score}" 
                       onchange="updatePriorityMeta('${country}', '${item.name}', 'score', this.value)" 
                       style="width:70px;margin:0;">
                <button class="btn-x" onclick="deletePriority('${country}', '${item.name}')">×</button>
            </div>
        `;
        container.appendChild(div);
    });
}

// Unified Update Function
window.updatePriorityMeta = (c, name, key, val) => { 
    // Ensure object structure exists
    let current = configData.sport_priorities[c][name];
    if (typeof current === 'number') current = { score: current, isLeague: false, hasLink: false };
    
    if (key === 'score') current.score = parseInt(val);
    else current[key] = val; // boolean

    configData.sport_priorities[c][name] = current;
    // Don't re-render instantly to avoid losing focus, or do if strictly needed
};

window.deletePriority = (c, s) => { delete configData.sport_priorities[c][s]; renderPriorities(); };

window.addPriorityRow = () => {
    const c = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        // Default new item
        configData.sport_priorities[c][name] = { score: 50, isLeague: false, hasLink: false };
        setVal('newSportName', '');
        renderPriorities();
    }
};

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

// ==========================================
// 6. SAVING & POLLING
// ==========================================
document.getElementById('saveBtn').onclick = async () => {
    if(isBuilding) return;
    
    const token = localStorage.getItem('gh_token');
    updateStatus('building', 'Saving & Triggering Build...');
    document.getElementById('saveBtn').disabled = true;
    captureAllInputs();

    const jsonStr = JSON.stringify(configData, null, 2);
    const content = btoa(unescape(encodeURIComponent(jsonStr)));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 
                'Authorization': `token ${token}`, 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ 
                message: "CMS Update: Trigger Build", 
                content: content, 
                sha: currentSha, 
                branch: BRANCH 
            })
        });

        if(res.ok) {
            const data = await res.json();
            currentSha = data.content.sha;
            startPolling(); 
        } else {
            const err = await res.json();
            throw new Error(err.message || "Save failed");
        }
    } catch(e) { 
        updateStatus('error', 'Save Failed');
        document.getElementById('saveBtn').disabled = false;
        alert("Error: " + e.message); 
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

// ==========================================
// 7. UTILS
// ==========================================
function updateStatus(state, text) {
    const box = document.getElementById('buildStatusBox');
    const txt = document.getElementById('buildStatusText');
    if(box && txt) {
        box.className = `build-box ${state}`;
        txt.textContent = text;
    }
}
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
function setupInputs() { /* Listeners */ }

window.switchTab = (id) => {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
};
