// ==========================================
// 1. CONFIGURATION (EDIT THIS!)
// ==========================================
const REPO_OWNER = 'arkhan66648'; // <--- CHANGE TO YOUR GITHUB USERNAME
const REPO_NAME = 'project1';     // <--- CHANGE TO YOUR REPO NAME
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
    document.getElementById('ghToken').focus();
}

// CALLED BY LOGIN BUTTON
window.saveToken = async () => {
    const token = document.getElementById('ghToken').value.trim();
    if(!token) return alert("Please enter a token");
    
    const btn = document.querySelector('#authModal .save-btn');
    const originalText = btn.innerText;
    btn.innerText = "Verifying...";
    btn.disabled = true;

    try {
        // Test connection to the REPO
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}`, {
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });

        if (res.status === 200) {
            localStorage.setItem('gh_token', token);
            document.getElementById('authModal').style.display = 'none';
            verifyAndLoad(token);
        } else if (res.status === 404) {
            alert(`Token valid, but Repo "${REPO_OWNER}/${REPO_NAME}" not found. Check constants in app.js.`);
        } else if (res.status === 401) {
            alert("Invalid Token. Please check permissions.");
        } else {
            alert(`Error: ${res.statusText}`);
        }
    } catch(e) {
        alert("Connection Error: " + e.message);
    }

    btn.innerText = originalText;
    btn.disabled = false;
};

// LOAD DATA
async function verifyAndLoad(token) {
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.status === 401) {
            // Token expired or revoked
            localStorage.removeItem('gh_token');
            showLoginModal();
            return;
        }

        if (res.status === 404) {
            console.warn("Config not found. Initializing Demo.");
            configData = JSON.parse(JSON.stringify(DEMO_CONFIG));
            populateUI();
            return;
        }

        const data = await res.json();
        currentSha = data.sha;
        const decoded = decodeURIComponent(escape(atob(data.content))); // Robust UTF-8 decoding
        configData = JSON.parse(decoded);
        
        populateUI();
        startPolling(); // Start watching build status

    } catch (e) {
        console.error("Critical Load Error", e);
        alert("Failed to load config. See console.");
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

    if(document.getElementById('colPrimary')) document.getElementById('colPrimary').value = t.brand_primary || '#D00000';

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
    
    configData.theme = {
        ...(configData.theme || {}),
        brand_primary: getVal('colPrimary')
    };
    
    // Pages captured via TinyMCE event
}

// ==========================================
// 5. PRIORITIES & MENUS
// ==========================================
function renderPriorities() {
    const country = getVal('targetCountry') || 'US';
    const container = document.getElementById('priorityListContainer');
    if(!container) return;
    
    // Update Label
    const lbl = document.getElementById('prioLabel');
    if(lbl) lbl.innerText = country;

    // Safety Init
    if (!configData.sport_priorities[country]) configData.sport_priorities[country] = {};

    container.innerHTML = '';
    const sorted = Object.entries(configData.sport_priorities[country]).sort((a,b) => b[1] - a[1]);
    
    sorted.forEach(([sport, score]) => {
        const div = document.createElement('div');
        div.className = 'menu-item-row';
        div.innerHTML = `
            <strong>${sport}</strong>
            <div style="display:flex; gap:10px; align-items:center;">
                <input type="number" value="${score}" onchange="updatePriority('${country}', '${sport}', this.value)" style="width:60px;margin:0;">
                <button class="btn-x" onclick="deletePriority('${country}', '${sport}')">×</button>
            </div>
        `;
        container.appendChild(div);
    });
}

window.updatePriority = (c, s, v) => { configData.sport_priorities[c][s] = parseInt(v); };
window.deletePriority = (c, s) => { delete configData.sport_priorities[c][s]; renderPriorities(); };
window.addPriorityRow = () => {
    const c = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        configData.sport_priorities[c][name] = 50;
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

    // UTF-8 Safe Encoding
    const jsonStr = JSON.stringify(configData, null, 2);
    const content = btoa(unescape(encodeURIComponent(jsonStr)));
    
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 
                'Authorization': `Bearer ${token}`, 
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
            startPolling(); // Start watching the Actions tab
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
    pollingInterval = setInterval(checkBuildStatus, 5000); // Check every 5s
}

async function checkBuildStatus() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1`, {
            headers: { 'Authorization': `Bearer ${token}` }
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
function setupInputs() { /* Add any extra listeners here */ }

window.switchTab = (id) => {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
};
