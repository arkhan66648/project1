// ==========================================
// 1. CONFIGURATION
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';     
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// ==========================================
// 2. DEMO DATA (New Structure)
// ==========================================
const DEMO_CONFIG = {
    site_settings: {
        title_part_1: "Stream", title_part_2: "East", domain: "streameast.to",
        logo_url: "", target_country: "US"
    },
    theme: {
        brand_primary: "#D00000", brand_dark: "#8a0000", accent_gold: "#FFD700",
        bg_body: "#050505", hero_gradient_start: "#1a0505", font_family: "system-ui"
    },
    sport_priorities: { 
        US: { "NBA": { score: 100, isLeague: true, hasLink: true } },
        UK: { "Premier League": { score: 100, isLeague: true, hasLink: true } }
    },
    menus: {
        header: [{ title: "Schedule", url: "#" }],
        hero: [{ title: "NBA", url: "#" }],
        footer_links: [{ title: "NFL", url: "#" }],
        footer_static: [{ title: "DMCA", url: "/dmca" }]
    },
    entity_stacking: [
        { keyword: "NBA Streams Free", content: "<p>Watch the best NBA Streams here...</p>" }
    ],
    pages: [
        { 
            id: "p_home", title: "Home", slug: "home", layout: "home", 
            meta_title: "Live Sports", meta_desc: "Watch free sports...", 
            content: "Welcome...", schemas: { live: true, upcoming: true } 
        }
    ]
};

let configData = {};
let currentSha = null;
let currentEditingPageId = null;
let isBuilding = false;

// ==========================================
// 3. INITIALIZATION
// ==========================================
window.addEventListener("DOMContentLoaded", () => {
    // Init TinyMCE
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { ed.on('change', saveEditorContentToMemory); }
        });
    }

    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else verifyAndLoad(token);
});

window.saveToken = async () => {
    const token = document.getElementById('ghToken').value.trim();
    if(token) {
        localStorage.setItem('gh_token', token);
        document.getElementById('authModal').style.display = 'none';
        verifyAndLoad(token);
    }
};

async function verifyAndLoad(token) {
    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}` }
        });
        
        if(res.status === 404) {
            configData = JSON.parse(JSON.stringify(DEMO_CONFIG));
            populateUI();
            return;
        }

        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(decodeURIComponent(escape(atob(data.content))));
        
        // Data Migration/Safety
        if(!configData.menus) configData.menus = DEMO_CONFIG.menus;
        if(!configData.entity_stacking) configData.entity_stacking = [];
        if(!configData.pages) configData.pages = DEMO_CONFIG.pages;
        
        populateUI();
        startPolling();
    } catch(e) { console.error(e); }
}

// ==========================================
// 4. UI POPULATION
// ==========================================
function populateUI() {
    // General
    const s = configData.site_settings;
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('targetCountry', s.target_country || 'US');

    // Appearance
    const t = configData.theme;
    setVal('brandPrimary', t.brand_primary);
    setVal('brandDark', t.brand_dark);
    setVal('accentGold', t.accent_gold);
    setVal('bgBody', t.bg_body);
    setVal('heroGradient', t.hero_gradient_start);
    setVal('fontFamily', t.font_family);

    // Lists
    renderPriorities();
    renderMenus();
    renderEntityStacking();
    renderPageList();
}

// ==========================================
// 5. PAGES SYSTEM (WordPress Style)
// ==========================================
function renderPageList() {
    const tbody = document.querySelector('#pagesTable tbody');
    tbody.innerHTML = configData.pages.map(p => `
        <tr>
            <td><strong>${p.title}</strong></td>
            <td>/${p.slug}</td>
            <td>${p.layout}</td>
            <td>
                <button class="btn-primary" onclick="editPage('${p.id}')">Edit</button>
                ${p.slug !== 'home' ? `<button class="btn-danger" onclick="deletePage('${p.id}')">Del</button>` : ''}
            </td>
        </tr>
    `).join('');
}

window.createNewPage = () => {
    const id = 'p_' + Date.now();
    configData.pages.push({
        id, title: "New Page", slug: "new-page", layout: "page",
        meta_title: "", meta_desc: "", content: "", schemas: {}
    });
    renderPageList();
    editPage(id);
};

window.editPage = (id) => {
    currentEditingPageId = id;
    const p = configData.pages.find(x => x.id === id);
    if(!p) return;

    // Show Editor
    document.getElementById('pageListView').style.display = 'none';
    document.getElementById('pageEditorView').style.display = 'block';
    document.getElementById('editorPageTitleDisplay').innerText = `Editing: ${p.title}`;

    // Fill Inputs
    setVal('pageTitle', p.title);
    setVal('pageSlug', p.slug);
    setVal('pageLayout', p.layout);
    setVal('pageMetaTitle', p.meta_title);
    setVal('pageMetaDesc', p.meta_desc);
    
    // Checkboxes
    document.getElementById('schemaLive').checked = p.schemas?.live || false;
    document.getElementById('schemaUpcoming').checked = p.schemas?.upcoming || false;
    document.getElementById('schemaOrg').checked = p.schemas?.org || false;

    // Content
    if(tinymce.get('pageContentEditor')) tinymce.get('pageContentEditor').setContent(p.content || '');

    // Slug Lock for Home
    document.getElementById('pageSlug').disabled = (p.slug === 'home');
};

window.closePageEditor = () => {
    saveEditorContentToMemory(); // Ensure latest state is saved
    document.getElementById('pageEditorView').style.display = 'none';
    document.getElementById('pageListView').style.display = 'block';
    renderPageList();
};

function saveEditorContentToMemory() {
    if(!currentEditingPageId) return;
    const p = configData.pages.find(x => x.id === currentEditingPageId);
    if(!p) return;

    p.title = getVal('pageTitle');
    p.slug = getVal('pageSlug');
    p.layout = getVal('pageLayout');
    p.meta_title = getVal('pageMetaTitle');
    p.meta_desc = getVal('pageMetaDesc');
    p.content = tinymce.get('pageContentEditor').getContent();
    
    p.schemas = {
        live: document.getElementById('schemaLive').checked,
        upcoming: document.getElementById('schemaUpcoming').checked,
        org: document.getElementById('schemaOrg').checked
    };
}

window.deletePage = (id) => {
    if(confirm("Delete this page?")) {
        configData.pages = configData.pages.filter(p => p.id !== id);
        renderPageList();
    }
};

// ==========================================
// 6. MENUS & ENTITIES
// ==========================================
function renderMenus() {
    ['header', 'hero', 'footer_links', 'footer_static'].forEach(sec => {
        const div = document.getElementById(`menu-${sec}`);
        div.innerHTML = (configData.menus[sec] || []).map((item, idx) => `
            <div class="menu-item-row">
                <div><strong>${item.title}</strong> <small>(${item.url})</small></div>
                <button class="btn-icon" onclick="deleteMenuItem('${sec}', ${idx})">×</button>
            </div>
        `).join('');
    });
}

window.openMenuModal = (sec) => {
    document.getElementById('menuTargetSection').value = sec;
    setVal('menuTitleItem', ''); setVal('menuUrlItem', '');
    document.getElementById('menuModal').style.display = 'flex';
};

window.saveMenuItem = () => {
    const sec = document.getElementById('menuTargetSection').value;
    const item = { title: getVal('menuTitleItem'), url: getVal('menuUrlItem') };
    if(!configData.menus[sec]) configData.menus[sec] = [];
    configData.menus[sec].push(item);
    renderMenus();
    document.getElementById('menuModal').style.display = 'none';
};

window.deleteMenuItem = (sec, idx) => {
    configData.menus[sec].splice(idx, 1);
    renderMenus();
};

// --- Entity Stacking ---
function renderEntityStacking() {
    const list = document.getElementById('entityList');
    list.innerHTML = configData.entity_stacking.map((e, idx) => `
        <div class="menu-item-row">
            <strong>${e.keyword}</strong>
            <div>
                <button class="btn-primary" style="font-size:0.7rem;" onclick="openEntityEditor(${idx})">Edit Popup</button>
                <button class="btn-icon" onclick="deleteEntityRow(${idx})">×</button>
            </div>
        </div>
    `).join('');
}

window.addEntityRow = () => {
    const kw = getVal('newEntityKeyword');
    if(kw) {
        configData.entity_stacking.push({ keyword: kw, content: `<h3>${kw}</h3><p>Find the best streams for ${kw} on our site.</p>` });
        setVal('newEntityKeyword', '');
        renderEntityStacking();
    }
};

window.openEntityEditor = (idx) => {
    const e = configData.entity_stacking[idx];
    document.getElementById('entityIndex').value = idx;
    setVal('entityKeywordEdit', e.keyword);
    setVal('entityContentEdit', e.content);
    document.getElementById('entityModal').style.display = 'flex';
};

window.saveEntityContent = () => {
    const idx = document.getElementById('entityIndex').value;
    configData.entity_stacking[idx].content = getVal('entityContentEdit');
    document.getElementById('entityModal').style.display = 'none';
};

window.deleteEntityRow = (idx) => {
    configData.entity_stacking.splice(idx, 1);
    renderEntityStacking();
};

// ==========================================
// 7. PRIORITIES (Updated for Step 2)
// ==========================================
function renderPriorities() {
    const c = getVal('targetCountry');
    const container = document.getElementById('priorityListContainer');
    document.getElementById('prioLabel').innerText = c;
    
    if(!configData.sport_priorities[c]) configData.sport_priorities[c] = {};
    
    // Sort logic
    const items = Object.entries(configData.sport_priorities[c])
        .map(([name, data]) => ({ name, ...data }))
        .sort((a,b) => b.score - a.score);

    container.innerHTML = items.map(item => `
        <div class="menu-item-row" style="flex-wrap:wrap;">
            <strong style="width:140px;">${item.name}</strong>
            <div style="flex:1; display:flex; gap:10px; align-items:center;">
                <label style="margin:0; font-size:0.75rem;"><input type="checkbox" ${item.isLeague?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','isLeague',this.checked)"> Is League</label>
                <label style="margin:0; font-size:0.75rem;"><input type="checkbox" ${item.hasLink?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','hasLink',this.checked)"> Link</label>
                <input type="number" value="${item.score}" onchange="updatePrioMeta('${c}','${item.name}','score',this.value)" style="width:60px; margin:0;">
                <button class="btn-icon" onclick="deletePriority('${c}', '${item.name}')">×</button>
            </div>
        </div>
    `).join('');
}

window.addPriorityRow = () => {
    const c = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        configData.sport_priorities[c][name] = { score: 50, isLeague: false, hasLink: false };
        setVal('newSportName', '');
        renderPriorities();
    }
};

window.updatePrioMeta = (c, name, key, val) => {
    const item = configData.sport_priorities[c][name];
    if(key === 'score') item.score = parseInt(val);
    else item[key] = val;
};
window.deletePriority = (c, name) => {
    delete configData.sport_priorities[c][name];
    renderPriorities();
};

// ==========================================
// 8. GLOBAL SAVE
// ==========================================
function captureAll() {
    // Save current editor state if open
    if(document.getElementById('pageEditorView').style.display === 'block') saveEditorContentToMemory();

    configData.site_settings = {
        title_part_1: getVal('titleP1'),
        title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        target_country: getVal('targetCountry')
    };
    
    configData.theme = {
        brand_primary: getVal('brandPrimary'),
        brand_dark: getVal('brandDark'),
        accent_gold: getVal('accentGold'),
        bg_body: getVal('bgBody'),
        hero_gradient_start: getVal('heroGradient'),
        font_family: getVal('fontFamily')
    };
}

document.getElementById('saveBtn').onclick = async () => {
    if(isBuilding) return;
    captureAll();
    
    document.getElementById('saveBtn').innerText = "Saving...";
    document.getElementById('saveBtn').disabled = true;

    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));
    const token = localStorage.getItem('gh_token');

    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "CMS Update", content, sha: currentSha, branch: BRANCH })
        });

        if(res.ok) {
            const d = await res.json();
            currentSha = d.content.sha;
            startPolling();
        } else alert("Save failed");
    } catch(e) { alert("Error: " + e.message); }
};

function startPolling() {
    document.getElementById('saveBtn').innerText = "Building...";
    const iv = setInterval(async () => {
        const token = localStorage.getItem('gh_token');
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1`, {
            headers: { 'Authorization': `token ${token}` }
        });
        const d = await res.json();
        const run = d.workflow_runs[0];
        
        if(run.status === 'completed') {
            clearInterval(iv);
            isBuilding = false;
            document.getElementById('saveBtn').disabled = false;
            document.getElementById('saveBtn').innerText = "💾 Save & Build Site";
            document.getElementById('buildStatusText').innerText = run.conclusion === 'success' ? "Live ✅" : "Failed ❌";
            document.getElementById('buildStatusBox').className = `build-box ${run.conclusion}`;
        } else {
            document.getElementById('buildStatusText').innerText = "Building...";
            document.getElementById('buildStatusBox').className = "build-box building";
        }
    }, 5000);
}

// Utils
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
window.updatePreview = () => {}; // Can add real-time CSS var updates here
window.switchTab = (id) => {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
};
