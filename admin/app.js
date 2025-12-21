const REPO_OWNER = 'arkhan66648'; // CHANGE THIS
const REPO_NAME = 'project1';     // CHANGE THIS
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

let configData = {};
let currentSha = null;
let pollingInterval = null;

// INIT
window.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else {
        loadConfig();
        startPolling(); // Check status immediately on load
    }
    
    // Setup inputs (simplified for brevity)
    setupInputs();
});

async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        populateUI();
    } catch (e) { console.error("Load Error", e); }
}

// ==========================================
// 1. SAVE & TRIGGER BUILD
// ==========================================
document.getElementById('saveBtn').onclick = async () => {
    if(isBuilding) return; // Prevent double clicks
    
    const btn = document.getElementById('saveBtn');
    updateStatus('building', 'Saving & Triggering Build...');
    btn.disabled = true;

    // Capture Data from Inputs
    captureAllInputs();

    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    
    try {
        // PUT request updates config.json
        // GitHub Actions detects this push and AUTOMATICALLY starts the Python script
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
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
            // Now we wait for the GitHub Action to pick it up
            updateStatus('building', 'Build Queued...');
            startPolling(); 
        } else {
            throw new Error("Save Failed");
        }
    } catch(e) { 
        updateStatus('error', 'Save Failed');
        btn.disabled = false;
        alert(e.message); 
    }
};

// ==========================================
// 2. POLL BUILD STATUS (The Magic)
// ==========================================
let isBuilding = false;

function startPolling() {
    if(pollingInterval) clearInterval(pollingInterval);
    checkBuildStatus(); // Run once immediately
    pollingInterval = setInterval(checkBuildStatus, 5000); // Check every 5s
}

async function checkBuildStatus() {
    const token = localStorage.getItem('gh_token');
    try {
        // Get latest workflow runs
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1`, {
            headers: { 'Authorization': `token ${token}` }
        });
        const data = await res.json();
        
        if(data.workflow_runs && data.workflow_runs.length > 0) {
            const run = data.workflow_runs[0];
            const status = run.status; // queued, in_progress, completed
            const conclusion = run.conclusion; // success, failure, null

            if (status === 'queued' || status === 'in_progress') {
                isBuilding = true;
                document.getElementById('saveBtn').disabled = true;
                updateStatus('building', `Building... (${status})`);
            } else if (status === 'completed') {
                isBuilding = false;
                document.getElementById('saveBtn').disabled = false;
                
                if (conclusion === 'success') {
                    updateStatus('success', 'Site is Live ✅');
                    clearInterval(pollingInterval); // Stop polling when done
                } else {
                    updateStatus('error', 'Build Failed ❌');
                    clearInterval(pollingInterval);
                }
            }
        }
    } catch(e) { console.error("Polling error", e); }
}

function updateStatus(state, text) {
    const box = document.getElementById('buildStatusBox');
    const txt = document.getElementById('buildStatusText');
    box.className = `build-box ${state}`;
    txt.textContent = text;
}

// ==========================================
// UI HELPERS
// ==========================================
function captureAllInputs() {
    // Site Identity
    configData.site_settings = {
        title_part_1: getVal('titleP1'),
        title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        favicon: getVal('faviconUrl'),
        ga_id: getVal('gaId'),
        custom_meta: getVal('customMeta')
    };
    
    // Theme
    configData.theme = {
        brand_primary: getVal('colPrimary'),
        brand_dark: getVal('colDark'),
        accent_gold: getVal('colGold'),
        bg_body: getVal('colBg'),
        hero_gradient_start: getVal('colHeroStart')
    };
    // ... Add other inputs capture here ...
}

function populateUI() {
    const s = configData.site_settings || {};
    const t = configData.theme || {};
    
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('faviconUrl', s.favicon);
    setVal('gaId', s.ga_id);
    setVal('customMeta', s.custom_meta);

    setColor('colPrimary', 'txtPrimary', t.brand_primary);
    setColor('colDark', 'txtDark', t.brand_dark);
    setColor('colGold', 'txtGold', t.accent_gold);
    setColor('colBg', 'txtBg', t.bg_body);
    setColor('colHeroStart', 'txtHeroStart', t.hero_gradient_start);
}

function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
}

function saveToken() { localStorage.setItem('gh_token', document.getElementById('ghToken').value); location.reload(); }
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
function setColor(pid, tid, v) { setVal(pid, v); setVal(tid, v); }
function setupInputs() {
    document.querySelectorAll('input[type="color"]').forEach(el => {
        el.addEventListener('input', (e) => {
            const txtId = e.target.id.replace('col', 'txt');
            if(document.getElementById(txtId)) document.getElementById(txtId).value = e.target.value;
        });
    });
}
