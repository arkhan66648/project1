// ==========================================
// 1. CONFIGURATION
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1';     
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// ==========================================
// 2. DEFAULT DATA
// ==========================================
const DEFAULT_PRIORITIES = {
    US: {
        _HIDE_OTHERS: false, // Default to allowing other sports
        "NFL": { score: 100, isLeague: true, hasLink: true, isHidden: false },
        "NBA": { score: 95, isLeague: true, hasLink: true, isHidden: false },
        "MLB": { score: 90, isLeague: true, hasLink: true, isHidden: false },
        "College Football": { score: 88, isLeague: true, hasLink: false, isHidden: false },
        "NCAA": { score: 87, isLeague: true, hasLink: false, isHidden: false },
        "NHL": { score: 85, isLeague: true, hasLink: false, isHidden: false },
        "UFC": { score: 80, isLeague: true, hasLink: false, isHidden: false },
        "Premier League": { score: 75, isLeague: true, hasLink: false, isHidden: false },
        "MLS": { score: 70, isLeague: true, hasLink: false, isHidden: false },
        "Champions League": { score: 65, isLeague: true, hasLink: false, isHidden: false },
        "Boxing": { score: 50, isLeague: false, hasLink: false, isHidden: false },
        "Formula 1": { score: 45, isLeague: true, hasLink: false, isHidden: false },
        "Tennis": { score: 40, isLeague: false, hasLink: false, isHidden: false }
    },
    UK: {
        _HIDE_OTHERS: false,
        "Premier League": { score: 100, isLeague: true, hasLink: true, isHidden: false },
        "Champions League": { score: 95, isLeague: true, hasLink: true, isHidden: false },
        "Championship": { score: 90, isLeague: true, hasLink: false, isHidden: false },
        "The Ashes": { score: 85, isLeague: true, hasLink: false, isHidden: false },
        "Cricket": { score: 80, isLeague: false, hasLink: false, isHidden: false },
        "Rugby": { score: 75, isLeague: false, hasLink: false, isHidden: false },
        "Snooker": { score: 70, isLeague: false, hasLink: false, isHidden: false },
        "Darts": { score: 65, isLeague: false, hasLink: false, isHidden: false },
        "F1": { score: 60, isLeague: true, hasLink: true, isHidden: false },
        "Formula 1": { score: 60, isLeague: true, hasLink: true, isHidden: false },
        "Boxing": { score: 50, isLeague: false, hasLink: false, isHidden: false },
        "NFL": { score: 40, isLeague: true, hasLink: false, isHidden: false }
    }
};

const DEMO_CONFIG = {
    site_settings: {
        title_part_1: "Stream", title_part_2: "East", domain: "streameast.to",
        logo_url: "", target_country: "US"
    },
    social_sharing: {
        counts: { telegram: 1200, whatsapp: 800, reddit: 300, twitter: 500 },
        excluded_pages: "dmca,contact,about,privacy"
    },
    theme: {
        brand_primary: "#D00000", brand_dark: "#8a0000", accent_gold: "#FFD700",
        bg_body: "#050505", hero_gradient_start: "#1a0505", font_family: "system-ui"
    },
    sport_priorities: JSON.parse(JSON.stringify(DEFAULT_PRIORITIES)), 
    menus: { header: [], hero: [], footer_leagues: [], footer_static: [] },
    entity_stacking: [],
    pages: [
        { id: "p_home", title: "Home", slug: "home", layout: "home", meta_title: "Live Sports", content: "Welcome", schemas: { org: true, live: true, schedule: true } }
    ]
};

let configData = {};
let currentSha = null;
let currentEditingPageId = null;
let isBuilding = false;

// ==========================================
// 3. INITIALIZATION & INJECTION
// ==========================================
window.addEventListener("DOMContentLoaded", () => {
    // A. INJECT NEW UI ELEMENTS
    injectSocialTab();
    injectSchemaOptions();

    // B. INIT EDITOR
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { ed.on('change', saveEditorContentToMemory); }
        });
    }
    
    // C. RESET BTN INJECTION
    const prioHeader = document.querySelector('#tab-priorities .header-box');
    if(prioHeader && !document.getElementById('resetPrioBtn')) {
        const btn = document.createElement('button');
        btn.id = 'resetPrioBtn';
        btn.className = 'btn-danger';
        btn.innerText = 'Reset to Defaults';
        btn.onclick = resetPriorities;
        prioHeader.appendChild(btn);
    }

    // D. AUTH
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else verifyAndLoad(token);
});

// --- DYNAMIC UI INJECTION ---
function injectSocialTab() {
    const nav = document.querySelector('.sidebar nav');
    if(nav && !document.getElementById('nav-social')) {
        const btn = document.createElement('button');
        btn.className = 'nav-btn';
        btn.id = 'nav-social';
        btn.innerHTML = '💬 Social Sharing';
        btn.onclick = () => switchTab('social');
        nav.appendChild(btn);
    }

    const main = document.querySelector('.content-area');
    if(main && !document.getElementById('tab-social')) {
        const section = document.createElement('section');
        section.id = 'tab-social';
        section.className = 'tab-content';
        section.innerHTML = `
            <div class="header-box"><h1>Social Sharing Settings</h1></div>
            <div class="grid-2">
                <div class="card">
                    <h3>Fake Share Counts</h3>
                    <p class="desc">These numbers appear on the social buttons.</p>
                    <label>Telegram Count</label><input type="number" id="socialTelegram">
                    <label>WhatsApp Count</label><input type="number" id="socialWhatsapp">
                    <label>Reddit Count</label><input type="number" id="socialReddit">
                    <label>Twitter Count</label><input type="number" id="socialTwitter">
                </div>
                <div class="card">
                    <h3>Visibility Control</h3>
                    <label>Exclude on Pages (Slug separated by comma)</label>
                    <textarea id="socialExcluded" rows="4" placeholder="dmca, contact, privacy"></textarea>
                    <p class="desc">The share sidebar will NOT appear on these pages.</p>
                </div>
            </div>
        `;
        main.appendChild(section);
    }
}

function injectSchemaOptions() {
    const group = document.querySelector('#pageEditorView .checkbox-group');
    if(group && !document.getElementById('schemaLive')) {
        const lbl1 = document.createElement('label');
        lbl1.innerHTML = '<input type="checkbox" id="schemaLive"> Live Badge Schema (EventLive)';
        group.appendChild(lbl1);

        const lbl2 = document.createElement('label');
        lbl2.innerHTML = '<input type="checkbox" id="schemaSchedule"> Match Schedule Schema (ItemList)';
        group.appendChild(lbl2);
    }
}

// --- AUTH ---
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
        
        // --- DATA MIGRATION ---
        if(!configData.pages) configData.pages = DEMO_CONFIG.pages;
        configData.pages.forEach(p => { if(!p.id) p.id = 'p_' + Math.random().toString(36).substr(2, 9); });
        
        // Initialize priorities if missing
        if(!configData.sport_priorities) configData.sport_priorities = JSON.parse(JSON.stringify(DEFAULT_PRIORITIES));
        if(!configData.sport_priorities.US) configData.sport_priorities.US = { _HIDE_OTHERS: false };
        if(!configData.sport_priorities.UK) configData.sport_priorities.UK = { _HIDE_OTHERS: false };

        if(!configData.menus.footer_leagues) configData.menus.footer_leagues = [];
        if(!configData.social_sharing) configData.social_sharing = DEMO_CONFIG.social_sharing;
        
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

    const soc = configData.social_sharing || { counts: {} };
    setVal('socialTelegram', soc.counts?.telegram || 0);
    setVal('socialWhatsapp', soc.counts?.whatsapp || 0);
    setVal('socialReddit', soc.counts?.reddit || 0);
    setVal('socialTwitter', soc.counts?.twitter || 0);
    setVal('socialExcluded', soc.excluded_pages || "");

    renderPriorities();
    renderMenus();
    renderEntityStacking();
    renderPageList();
}

// ==========================================
// 5. PRIORITIES (Updated with Hide Others)
// ==========================================
function renderPriorities() {
    const c = getVal('targetCountry') || 'US';
    const container = document.getElementById('priorityListContainer');
    if(document.getElementById('prioLabel')) document.getElementById('prioLabel').innerText = c;
    
    // Ensure data integrity
    if(!configData.sport_priorities[c]) configData.sport_priorities[c] = { _HIDE_OTHERS: false };

    // 1. Render Global Country Settings (Hide Others Checkbox)
    const isHideOthers = !!configData.sport_priorities[c]._HIDE_OTHERS;
    
    // 2. Render List
    const items = Object.entries(configData.sport_priorities[c])
        .filter(([name]) => name !== '_HIDE_OTHERS') // Filter out the setting key
        .map(([name, data]) => ({ name, ...data }))
        .sort((a,b) => b.score - a.score);

    // Build HTML
    let html = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 15px; border-radius: 6px; margin-bottom: 20px;">
            <label style="margin:0; font-weight:700; color:#fca5a5; display:flex; align-items:center; gap:10px;">
                <input type="checkbox" ${isHideOthers ? 'checked' : ''} onchange="toggleHideOthers('${c}', this.checked)"> 
                🚫 Hide all others (Strict Mode)
            </label>
            <p style="margin:5px 0 0 26px; font-size:0.8rem; color:#aaa;">
                If checked, only the leagues/sports listed below will be displayed in the upcoming section. Everything else from the backend will be hidden.
            </p>
        </div>
    `;

    html += items.map(item => `
        <div class="menu-item-row" style="flex-wrap:wrap; opacity: ${item.isHidden ? '0.5' : '1'};">
            <strong style="width:140px; overflow:hidden;">${item.name}</strong>
            <div style="flex:1; display:flex; gap:10px; align-items:center;">
                <label style="margin:0; font-size:0.75rem;">
                    <input type="checkbox" ${item.isLeague?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','isLeague',this.checked)"> League
                </label>
                <label style="margin:0; font-size:0.75rem;">
                    <input type="checkbox" ${item.hasLink?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','hasLink',this.checked)"> Link
                </label>
                <label style="margin:0; font-size:0.75rem; color:#ef4444;">
                    <input type="checkbox" ${item.isHidden?'checked':''} onchange="updatePrioMeta('${c}','${item.name}','isHidden',this.checked)"> Hide
                </label>
                <input type="number" value="${item.score}" onchange="updatePrioMeta('${c}','${item.name}','score',this.value)" style="width:60px; margin:0;">
                <button class="btn-icon" onclick="deletePriority('${c}', '${item.name}')">×</button>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

window.toggleHideOthers = (c, checked) => {
    if(!configData.sport_priorities[c]) configData.sport_priorities[c] = {};
    configData.sport_priorities[c]._HIDE_OTHERS = checked;
    // No re-render needed for checkbox toggle, acts like input
};

window.resetPriorities = () => {
    const c = getVal('targetCountry');
    if(!confirm(`Reset priorities for ${c} to default settings?`)) return;
    
    // Deep copy default
    const defaults = JSON.parse(JSON.stringify(DEFAULT_PRIORITIES[c] || DEFAULT_PRIORITIES['US']));
    configData.sport_priorities[c] = defaults;
    
    renderPriorities();
};

window.addPriorityRow = () => {
    const c = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        if(!configData.sport_priorities[c]) configData.sport_priorities[c] = { _HIDE_OTHERS: false };
        // Determine if it looks like a league (simple heuristic, user can change)
        const isLikelyLeague = name.toLowerCase().includes('league') || name.toLowerCase().includes('nba') || name.toLowerCase().includes('nfl');
        configData.sport_priorities[c][name] = { score: 50, isLeague: isLikelyLeague, hasLink: false, isHidden: false };
        setVal('newSportName', '');
        renderPriorities();
    }
};

window.updatePrioMeta = (c, name, key, val) => {
    const item = configData.sport_priorities[c][name];
    if(key === 'score') item.score = parseInt(val);
    else item[key] = val;
    if(key === 'isHidden') renderPriorities(); // Re-render to show opacity change
};

window.deletePriority = (c, name) => {
    if(confirm(`Remove ${name} from priorities?`)) {
        delete configData.sport_priorities[c][name];
        renderPriorities();
    }
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
    if(document.getElementById('schemaLive')) document.getElementById('schemaLive').checked = !!p.schemas.live;
    if(document.getElementById('schemaSchedule')) document.getElementById('schemaSchedule').checked = !!p.schemas.schedule;

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
        org: document.getElementById('schemaOrg').checked,
        live: document.getElementById('schemaLive') ? document.getElementById('schemaLive').checked : false,
        schedule: document.getElementById('schemaSchedule') ? document.getElementById('schemaSchedule').checked : false
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
    configData.pages.push({ id, title: "New Page", slug: "new-page", layout: "page", content: "", schemas: { org: true } });
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
            div.innerHTML = (configData.menus[sec] || []).map((item, idx) => {
                const hl = item.highlight ? '<span style="color:#facc15">★</span>' : '';
                return `
                <div class="menu-item-row">
                    <div>${hl} <strong>${item.title}</strong> <small>(${item.url})</small></div>
                    <button class="btn-icon" onclick="deleteMenuItem('${sec}', ${idx})">×</button>
                </div>
            `;
            }).join('');
        }
    });
}

window.openMenuModal = (sec) => { 
    document.getElementById('menuTargetSection').value = sec; 
    setVal('menuTitleItem',''); 
    setVal('menuUrlItem',''); 
    const modalContent = document.querySelector('#menuModal .modal-content');
    const existingCheck = document.getElementById('menuHighlightCheck');
    if(existingCheck) existingCheck.parentNode.remove();
    if(sec === 'header') {
        const wrap = document.createElement('div');
        wrap.innerHTML = `<label style="display:inline-flex; align-items:center; gap:5px; margin-top:10px;"><input type="checkbox" id="menuHighlightCheck"> Highlight this link (Gold Color)</label>`;
        modalContent.insertBefore(wrap, modalContent.querySelector('.modal-actions'));
    }
    document.getElementById('menuModal').style.display='flex'; 
};

window.saveMenuItem = () => { 
    const sec = document.getElementById('menuTargetSection').value;
    const isHighlight = document.getElementById('menuHighlightCheck') ? document.getElementById('menuHighlightCheck').checked : false;
    const item = { 
        title: getVal('menuTitleItem'), 
        url: getVal('menuUrlItem'),
        highlight: sec === 'header' ? isHighlight : false 
    };
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
            <div><button class="btn-icon" onclick="deleteEntityRow(${idx})">×</button></div>
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
    saveEditorContentToMemory(); 
    
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

    configData.social_sharing = {
        counts: {
            telegram: getVal('socialTelegram'),
            whatsapp: getVal('socialWhatsapp'), 
            reddit: getVal('socialReddit'),
            twitter: getVal('socialTwitter')
        },
        excluded_pages: getVal('socialExcluded')
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

window.switchTab = (id) => {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(e => e.classList.remove('active'));
    const target = document.getElementById(`tab-${id}`);
    if(target) target.classList.add('active');
    
    // Find nav button
    let btn = document.getElementById(`nav-${id}`);
    // Fallback if triggered via onClick this context
    if(!btn) {
        document.querySelectorAll('.nav-btn').forEach(b => {
            if(b.onclick.toString().includes(id)) btn = b;
        });
    }
    if(btn) {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
};

function setVal(id, v) { if(document.getElementById(id)) document.getElementById(id).value = v || ""; }
function getVal(id) { return document.getElementById(id)?.value || ""; }
window.updatePreview = () => {};
