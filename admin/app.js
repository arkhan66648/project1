// ==========================================
// 1. CONFIGURATION
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';     
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// ==========================================
// 2. DEFAULT DATA (UPDATED FOR NEW BACKEND)
// ==========================================
const DEFAULT_PRIORITIES = {
    US: [
        { name: "NFL", score: 100, isLeague: true, hasLink: true },
        { name: "NBA", score: 95, isLeague: true, hasLink: true },
        { name: "MLB", score: 90, isLeague: true, hasLink: true },
        { name: "College Football", score: 88, isLeague: true, hasLink: false },
        { name: "NCAA", score: 87, isLeague: true, hasLink: false },
        { name: "NHL", score: 85, isLeague: true, hasLink: false },
        { name: "UFC", score: 80, isLeague: true, hasLink: false },
        { name: "Premier League", score: 75, isLeague: true, hasLink: false },
        { name: "MLS", score: 70, isLeague: true, hasLink: false },
        { name: "Champions League", score: 65, isLeague: true, hasLink: false },
        { name: "Boxing", score: 50, isLeague: false, hasLink: false },
        { name: "Formula 1", score: 45, isLeague: true, hasLink: false },
        { name: "Tennis", score: 40, isLeague: false, hasLink: false }
    ],
    UK: [
        { name: "Premier League", score: 100, isLeague: true, hasLink: true },
        { name: "Champions League", score: 95, isLeague: true, hasLink: true },
        { name: "Championship", score: 90, isLeague: true, hasLink: false },
        { name: "The Ashes", score: 85, isLeague: true, hasLink: false },
        { name: "Cricket", score: 80, isLeague: false, hasLink: false },
        { name: "Rugby", score: 75, isLeague: false, hasLink: false },
        { name: "Snooker", score: 70, isLeague: false, hasLink: false },
        { name: "Darts", score: 65, isLeague: false, hasLink: false },
        { name: "F1", score: 60, isLeague: true, hasLink: true },
        { name: "Formula 1", score: 60, isLeague: true, hasLink: true },
        { name: "Boxing", score: 50, isLeague: false, hasLink: false },
        { name: "NFL", score: 40, isLeague: true, hasLink: false }
    ]
};

const DEMO_CONFIG = {
    site_settings: {
        title_part_1: "Stream", title_part_2: "East", domain: "streameast.to",
        logo_url: "", target_country: "US"
    },
    theme: {
        brand_primary: "#D00000", brand_dark: "#8a0000", accent_gold: "#FFD700",
        bg_body: "#050505", hero_gradient_start: "#1a0505", font_family: "system-ui"
    },
    sport_priorities: { US: {}, UK: {} }, 
    menus: { header: [], hero: [], footer_leagues: [], footer_static: [] },
    entity_stacking: [],
    pages: [
        { id: "p_home", title: "Home", slug: "home", layout: "home", meta_title: "Live Sports", content: "Welcome", schemas: { org: true } }
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
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { ed.on('change', saveEditorContentToMemory); }
        });
    }
    
    // Add "Reset" Button to Priority Section dynamically if not present
    const prioHeader = document.querySelector('#tab-priorities .header-box');
    if(prioHeader && !document.getElementById('resetPrioBtn')) {
        const btn = document.createElement('button');
        btn.id = 'resetPrioBtn';
        btn.className = 'btn-danger';
        btn.innerText = 'Reset to Defaults';
        btn.onclick = resetPriorities;
        prioHeader.appendChild(btn);
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
        
        // --- DATA MIGRATION FIXES ---
        if(!configData.pages) configData.pages = DEMO_CONFIG.pages;
        configData.pages.forEach(p => { if(!p.id) p.id = 'p_' + Math.random().toString(36).substr(2, 9); });
        if(!configData.sport_priorities) configData.sport_priorities = { US: {}, UK: {} };
        if(!configData.menus.footer_leagues) configData.menus.footer_leagues = [];
        
        populateUI();
        startPolling();
    } catch(e) { console.error(e); }
}

// ==========================================
// 4. UI POPULATION
// ==========================================
function populateUI() {
    const s = configData.site_settings || {};
    setVal('titleP1', s.title_part_1);
    setVal('titleP2', s.title_part_2);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('faviconUrl', s.favicon_url);
    setVal('footerCopyright', s.footer_copyright);
    setVal('footerDisclaimer', s.footer_disclaimer);
    setVal('targetCountry', s.target_country || 'US');

    const t = configData.theme || {};
    setVal('brandPrimary', t.brand_primary);
    setVal('brandDark', t.brand_dark);
    setVal('accentGold', t.accent_gold);
    setVal('bgBody', t.bg_body);
    setVal('heroGradient', t.hero_gradient_start);
    setVal('fontFamily', t.font_family);

    renderPriorities();
    renderMenus();
    renderEntityStacking();
    renderPageList();
}

// ==========================================
// 5. PRIORITIES (With Reset Logic)
// ==========================================
function renderPriorities() {
    const c = getVal('targetCountry') || 'US';
    const container = document.getElementById('priorityListContainer');
    document.getElementById('prioLabel').innerText = c;
    
    if(!configData.sport_priorities[c]) configData.sport_priorities[c] = {};
    
    // Sort logic
    const items = Object.entries(configData.sport_priorities[c])
        .map(([name, data]) => ({ name, ...data }))
        .sort((a,b) => b.score - a.score);

    container.innerHTML = items.map(item => `
        <div class="menu-item-row" style="flex-wrap:wrap;">
            <strong style="width:140px; overflow:hidden;">${item.name}</strong>
            <div style="flex:1; display:flex; gap:10px; align-items:center;">
                <label style="margin:0; font-size:0.75rem;"><input type="checkbox" ${item.isLeague?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','isLeague',this.checked)"> Is League</label>
                <label style="margin:0; font-size:0.75rem;"><input type="checkbox" ${item.hasLink?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','hasLink',this.checked)"> Link</label>
                <input type="number" value="${item.score}" onchange="updatePrioMeta('${c}','${item.name}','score',this.value)" style="width:60px; margin:0;">
                <button class="btn-icon" onclick="deletePriority('${c}', '${item.name}')">×</button>
            </div>
        </div>
    `).join('');
}

window.resetPriorities = () => {
    const c = getVal('targetCountry');
    if(!confirm(`Reset priorities for ${c} to default settings?`)) return;
    configData.sport_priorities[c] = {};
    const defaults = DEFAULT_PRIORITIES[c] || DEFAULT_PRIORITIES['US'];
    defaults.forEach(item => {
        configData.sport_priorities[c][item.name] = { score: item.score, isLeague: item.isLeague, hasLink: item.hasLink };
    });
    renderPriorities();
};

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
// 6. PAGES SYSTEM
// ==========================================
function renderPageList() {
    const tbody = document.querySelector('#pagesTable tbody');
    if(!configData.pages) configData.pages = [];
    
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

window.editPage = (id) => {
    currentEditingPageId = id;
    const p = configData.pages.find(x => x.id === id);
    if(!p) return;

    document.getElementById('pageListView').style.display = 'none';
    document.getElementById('pageEditorView').style.display = 'block';
    document.getElementById('editorPageTitleDisplay').innerText = `Editing: ${p.title}`;

    setVal('pageTitle', p.title);
    setVal('pageSlug', p.slug);
    setVal('pageLayout', p.layout || 'page');
    setVal('pageMetaTitle', p.meta_title);
    setVal('pageMetaDesc', p.meta_desc);
    setVal('pageMetaKeywords', p.meta_keywords); 
    setVal('pageCanonical', p.canonical_url); 
    
    if(!p.schemas) p.schemas = {};
    document.getElementById('schemaOrg').checked = !!p.schemas.org;

    if(tinymce.get('pageContentEditor')) tinymce.get('pageContentEditor').setContent(p.content || '');
    document.getElementById('pageSlug').disabled = (p.slug === 'home');
};

window.saveEditorContentToMemory = () => {
    if(!currentEditingPageId) return;
    const p = configData.pages.find(x => x.id === currentEditingPageId);
    if(!p) return;

    p.title = getVal('pageTitle');
    p.slug = getVal('pageSlug');
    p.layout = getVal('pageLayout');
    p.meta_title = getVal('pageMetaTitle');
    p.meta_desc = getVal('pageMetaDesc');
    p.meta_keywords = getVal('pageMetaKeywords');
    p.canonical_url = getVal('pageCanonical');
    p.content = tinymce.get('pageContentEditor').getContent();
    p.schemas = {
        org: document.getElementById('schemaOrg').checked
    };
};

window.closePageEditor = () => {
    saveEditorContentToMemory();
    document.getElementById('pageEditorView').style.display = 'none';
    document.getElementById('pageListView').style.display = 'block';
    renderPageList();
};

window.createNewPage = () => {
    const id = 'p_' + Date.now();
    configData.pages.push({ id, title: "New Page", slug: "new-page", layout: "page", content: "" });
    renderPageList();
    editPage(id);
};

window.deletePage = (id) => {
    if(confirm("Delete this page?")) {
        configData.pages = configData.pages.filter(p => p.id !== id);
        renderPageList();
    }
};

// ==========================================
// 7. MENUS & ENTITIES
// ==========================================
function renderMenus() {
    ['header', 'hero', 'footer_leagues', 'footer_static'].forEach(sec => {
        const div = document.getElementById(`menu-${sec}`);
        if(div) {
            div.innerHTML = (configData.menus[sec] || []).map((item, idx) => `
                <div class="menu-item-row">
                    <div><strong>${item.title}</strong> <small>(${item.url})</small></div>
                    <button class="btn-icon" onclick="deleteMenuItem('${sec}', ${idx})">×</button>
                </div>
            `).join('');
        }
    });
}
window.openMenuModal = (sec) => { document.getElementById('menuTargetSection').value = sec; setVal('menuTitleItem',''); setVal('menuUrlItem',''); document.getElementById('menuModal').style.display='flex'; };
window.saveMenuItem = () => { 
    const sec = document.getElementById('menuTargetSection').value;
    const item = { title: getVal('menuTitleItem'), url: getVal('menuUrlItem') };
    if(!configData.menus[sec]) configData.menus[sec] = [];
    configData.menus[sec].push(item);
    renderMenus();
    document.getElementById('menuModal').style.display = 'none';
};
window.deleteMenuItem = (sec, idx) => { configData.menus[sec].splice(idx, 1); renderMenus(); };

function renderEntityStacking() {
    const list = document.getElementById('entityList');
    if(!configData.entity_stacking) configData.entity_stacking = [];
    list.innerHTML = configData.entity_stacking.map((e, idx) => `
        <div class="menu-item-row">
            <strong>${e.keyword}</strong>
            <div>
                <button class="btn-icon" onclick="deleteEntityRow(${idx})">×</button>
            </div>
        </div>
    `).join('');
}
window.addEntityRow = () => {
    const kw = getVal('newEntityKeyword');
    if(kw) { configData.entity_stacking.push({ keyword: kw }); setVal('newEntityKeyword',''); renderEntityStacking(); }
};
window.deleteEntityRow = (idx) => { configData.entity_stacking.splice(idx, 1); renderEntityStacking(); };

// ==========================================
// 8. SAVE & UTILS
// ==========================================
document.getElementById('saveBtn').onclick = async () => {
    if(isBuilding) return;
    saveEditorContentToMemory(); // Capture page editor if open
    
    configData.site_settings = {
        title_part_1: getVal('titleP1'), title_part_2: getVal('titleP2'),
        domain: getVal('siteDomain'), logo_url: getVal('logoUrl'),
        favicon_url: getVal('faviconUrl'),
        footer_copyright: getVal('footerCopyright'),
        footer_disclaimer: getVal('footerDisclaimer'),
        target_country: getVal('targetCountry')
    };
    configData.theme = {
        brand_primary: getVal('brandPrimary'), brand_dark: getVal('brandDark'),
        accent_gold: getVal('accentGold'), bg_body: getVal('bgBody'),
        hero_gradient_start: getVal('heroGradient'), font_family: getVal('fontFamily')
    };

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
        } else alert("Save failed. Check console.");
    } catch(e) { alert("Error: " + e.message); }
};

function startPolling() {
    document.getElementById('saveBtn').innerText = "Building...";
    const iv = setInterval(async () => {
        const token = localStorage.getItem('gh_token');
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1`, { headers: { 'Authorization': `token ${token}` } });
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

// Tabs
window.switchTab = (id) => {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.currentTarget.classList.add('active');
};
function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
window.updatePreview = () => {};
