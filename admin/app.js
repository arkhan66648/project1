const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';     
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

let configData = { site_settings: {}, sport_priorities: { US: {}, UK: {} } };
let currentSha = null;
let isBuilding = false;

window.addEventListener("DOMContentLoaded", () => {
    if(typeof tinymce !== 'undefined') {
        tinymce.init({ selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { ed.on('change', () => { 
                let p = configData.pages.find(x => x.slug === 'home');
                if(p) p.content = ed.getContent();
            });} 
        });
    }
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();
});

async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, { headers: { 'Authorization': `token ${token}` } });
        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));
        populateUI();
    } catch (e) { console.error(e); }
}

function populateUI() {
    const s = configData.site_settings || {};
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('customMeta', s.custom_meta);
    setVal('targetCountry', s.target_country || 'US'); // Set Country

    const home = configData.pages.find(p => p.slug === 'home');
    if(home && tinymce.get('pageContentEditor')) tinymce.get('pageContentEditor').setContent(home.content || '');

    renderPriorities(); // Will render based on targetCountry
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
}

// --- PRIORITY LOGIC ---
function renderPriorities() {
    const country = getVal('targetCountry'); // Get currently selected country
    document.getElementById('prioLabel').innerText = country;
    
    // Ensure object exists
    if (!configData.sport_priorities[country]) configData.sport_priorities[country] = {};

    const container = document.getElementById('priorityListContainer');
    container.innerHTML = '';
    const sorted = Object.entries(configData.sport_priorities[country]).sort((a,b) => b[1] - a[1]);
    
    sorted.forEach(([sport, score]) => {
        const div = document.createElement('div');
        div.className = 'menu-item-row';
        div.innerHTML = `
            <strong>${sport}</strong>
            <div style="display:flex; gap:10px;">
                <input type="number" value="${score}" onchange="updatePriority('${country}', '${sport}', this.value)" style="width:60px;margin:0;">
                <button class="btn-x" onclick="deletePriority('${country}', '${sport}')">×</button>
            </div>`;
        container.appendChild(div);
    });
}

window.updatePriority = (country, sport, val) => { configData.sport_priorities[country][sport] = parseInt(val); };
window.deletePriority = (country, sport) => { delete configData.sport_priorities[country][sport]; renderPriorities(); };
window.addPriorityRow = () => {
    const country = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        configData.sport_priorities[country][name] = 50;
        setVal('newSportName', '');
        renderPriorities();
    }
};

// ... [Include standard Save, Menu, Utils, Polling functions here from previous code] ...
// (Shortened for brevity, use the same save logic as before)
document.getElementById('saveBtn').onclick = async () => {
    captureAllInputs();
    const token = localStorage.getItem('gh_token');
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
        method: 'PUT',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "Update CMS", content, sha: currentSha, branch: BRANCH })
    });
    alert("Saved! Build triggered.");
    location.reload();
};
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
function renderMenus() { /* ... */ } 
// ...
