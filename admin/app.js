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
        _HIDE_OTHERS: false, // Keep false to catch minor sports at the bottom
        
        // --- TIER 1: THE BIG 4 (Massive Traffic) ---
        "NFL": { score: 100, isLeague: true, hasLink: true, isHidden: false },
        "NBA": { score: 99, isLeague: true, hasLink: true, isHidden: false },
        "MLB": { score: 98, isLeague: true, hasLink: true, isHidden: false },
        "NHL": { score: 97, isLeague: true, hasLink: true, isHidden: false },
        
        // --- TIER 2: FIGHTING & RACING (High CPM/Value) ---
        "UFC": { score: 95, isLeague: true, hasLink: true, isHidden: false }, // "MMA" matches map here via alias
        "Boxing": { score: 94, isLeague: false, hasLink: true, isHidden: false }, // Individual events
        "Formula 1": { score: 93, isLeague: true, hasLink: true, isHidden: false },

        // --- TIER 3: COLLEGE SPORTS (Specific Entities) ---
        "College Football": { score: 90, isLeague: true, hasLink: true, isHidden: false }, // Maps to 'ncaaf'
        "College Basketball": { score: 89, isLeague: true, hasLink: true, isHidden: false }, // Maps to 'ncaab'

        // --- TIER 4: GLOBAL SOCCER (Specific Leagues > "Soccer") ---
        "Premier League": { score: 85, isLeague: true, hasLink: true, isHidden: false },
        "Champions League": { score: 84, isLeague: true, hasLink: true, isHidden: false },
        "MLS": { score: 83, isLeague: true, hasLink: true, isHidden: false },
        "LaLiga": { score: 82, isLeague: true, hasLink: true, isHidden: false },
        "Bundesliga": { score: 81, isLeague: true, hasLink: true, isHidden: false },
        "Serie A": { score: 80, isLeague: true, hasLink: true, isHidden: false },

        // --- TIER 5: LOW PRIORITY / CATCH-ALL ---
        "Tennis": { score: 40, isLeague: false, hasLink: true, isHidden: false }, // Grand Slams
        "Golf": { score: 30, isLeague: false, hasLink: false, isHidden: false }
    },
    UK: {
        _HIDE_OTHERS: false,

        // --- TIER 1: FOOTBALL IS KING ---
        "Premier League": { score: 100, isLeague: true, hasLink: true, isHidden: false },
        "Champions League": { score: 99, isLeague: true, hasLink: true, isHidden: false },
        "Championship": { score: 98, isLeague: true, hasLink: true, isHidden: false }, // EFL
        "Scottish Premiership": { score: 97, isLeague: true, hasLink: true, isHidden: false }, // SPFL
        "Europa League": { score: 96, isLeague: true, hasLink: true, isHidden: false },

        // --- TIER 2: TRADITIONAL UK SPORTS ---
        "Boxing": { score: 90, isLeague: false, hasLink: true, isHidden: false }, // Joshua/Fury fights
        "Formula 1": { score: 88, isLeague: true, hasLink: true, isHidden: false },
        "Cricket": { score: 85, isLeague: false, hasLink: true, isHidden: false }, // Ashes/IPL
        "Rugby": { score: 84, isLeague: false, hasLink: true, isHidden: false }, // Six Nations/Premiership
        "Darts": { score: 82, isLeague: false, hasLink: true, isHidden: false }, // PDC
        "Snooker": { score: 80, isLeague: false, hasLink: true, isHidden: false },

        // --- TIER 3: US IMPORTS ---
        "NFL": { score: 70, isLeague: true, hasLink: true, isHidden: false },
        "NBA": { score: 65, isLeague: true, hasLink: true, isHidden: false },
        "UFC": { score: 60, isLeague: true, hasLink: true, isHidden: false },

        // --- TIER 4: CATCH-ALL ---
        "Tennis": { score: 40, isLeague: false, hasLink: false, isHidden: false }
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
        { id: "p_home", title: "Home", slug: "home", layout: "home", meta_title: "Live Sports", content: "Welcome", schemas: { org: true, website: true } }
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
    // 1. Init Editor
    if(typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '#pageContentEditor', height: 400, skin: 'oxide-dark', content_css: 'dark',
            setup: (ed) => { ed.on('change', saveEditorContentToMemory); }
        });
    }
    
    // 2. Inject Reset Button for Priorities
    const prioHeader = document.querySelector('#tab-priorities .header-box');
    if(prioHeader && !document.getElementById('resetPrioBtn')) {
        const btn = document.createElement('button');
        btn.id = 'resetPrioBtn';
        btn.className = 'btn-danger';
        btn.innerText = 'Reset to Defaults';
        btn.onclick = resetPriorities;
        prioHeader.appendChild(btn);
    }

    // 3. Auth Check
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else verifyAndLoad(token);
});

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
        
        // --- DATA NORMALIZATION ---
        if(!configData.pages) configData.pages = DEMO_CONFIG.pages;
        configData.pages.forEach(p => { 
            if(!p.id) p.id = 'p_' + Math.random().toString(36).substr(2, 9); 
            if(!p.schemas) p.schemas = {};
            if(!p.schemas.faq_list) p.schemas.faq_list = [];
        });
        
        // Ensure Priorities Structure
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
// 5. PRIORITIES (With Hide Others)
// ==========================================
function renderPriorities() {
    const c = getVal('targetCountry') || 'US';
    const container = document.getElementById('priorityListContainer');
    if(document.getElementById('prioLabel')) document.getElementById('prioLabel').innerText = c;
    
    if(!configData.sport_priorities[c]) configData.sport_priorities[c] = { _HIDE_OTHERS: false };

    // 1. Hide Others Flag
    const isHideOthers = !!configData.sport_priorities[c]._HIDE_OTHERS;
    
    // 2. Sort Items
    const items = Object.entries(configData.sport_priorities[c])
        .filter(([name]) => name !== '_HIDE_OTHERS')
        .map(([name, data]) => ({ name, ...data }))
        .sort((a,b) => b.score - a.score);

    let html = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 15px; border-radius: 6px; margin-bottom: 20px;">
            <label style="margin:0; font-weight:700; color:#fca5a5; display:flex; align-items:center; gap:10px;">
                <input type="checkbox" ${isHideOthers ? 'checked' : ''} onchange="toggleHideOthers('${c}', this.checked)"> 
                🚫 Hide all others (Strict Mode)
            </label>
            <p style="margin:5px 0 0 26px; font-size:0.8rem; color:#aaa;">
                If checked, only the leagues/sports listed below will be displayed in the upcoming section.
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
};

window.resetPriorities = () => {
    const c = getVal('targetCountry');
    if(!confirm(`Reset priorities for ${c} to default settings?`)) return;
    const defaults = JSON.parse(JSON.stringify(DEFAULT_PRIORITIES[c] || DEFAULT_PRIORITIES['US']));
    configData.sport_priorities[c] = defaults;
    renderPriorities();
};

window.addPriorityRow = () => {
    const c = getVal('targetCountry');
    const name = getVal('newSportName');
    if(name) {
        if(!configData.sport_priorities[c]) configData.sport_priorities[c] = { _HIDE_OTHERS: false };
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
    if(key === 'isHidden') renderPriorities();
};

window.deletePriority = (c, name) => {
    if(confirm(`Remove ${name}?`)) {
        delete configData.sport_priorities[c][name];
        renderPriorities();
    }
};

// ==========================================
// 6. PAGES SYSTEM (New Schema & FAQ UI)
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
    
    // --- RENDER DYNAMIC SCHEMA UI ---
    if(!p.schemas) p.schemas = {};
    if(!p.schemas.faq_list) p.schemas.faq_list = [];

    const checkboxGroup = document.querySelector('#pageEditorView .checkbox-group');
    // Replace content entirely to match new requirements
    checkboxGroup.innerHTML = `
        <label style="color:#facc15; font-weight:700; border-bottom:1px solid #333; padding-bottom:5px; margin-bottom:10px;">Static Schemas (SEO)</label>
        <label><input type="checkbox" id="schemaOrg" ${p.schemas.org ? 'checked' : ''}> Organization Schema</label>
        <label><input type="checkbox" id="schemaWebsite" ${p.schemas.website ? 'checked' : ''}> WebSite Schema</label>
        <label><input type="checkbox" id="schemaFaq" ${p.schemas.faq ? 'checked' : ''} onchange="toggleFaqEditor(this.checked)"> FAQ Schema</label>
        
        <div id="faqEditorContainer" style="display:${p.schemas.faq ? 'block' : 'none'}; background:#0f172a; padding:15px; border:1px solid #334155; border-radius:6px; margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h4 style="margin:0; font-size:0.9rem;">FAQ Items</h4>
                <button class="btn-primary" style="padding:4px 10px; font-size:0.8rem;" onclick="addFaqItem()">+ Add Question</button>
            </div>
            <div id="faqList" style="display:flex; flex-direction:column; gap:10px;"></div>
        </div>
    `;

    // Render existing FAQs
    renderFaqItems(p.schemas.faq_list);

    if(tinymce.get('pageContentEditor')) tinymce.get('pageContentEditor').setContent(p.content || '');
    document.getElementById('pageSlug').disabled = (p.slug === 'home');
};

window.toggleFaqEditor = (isChecked) => {
    document.getElementById('faqEditorContainer').style.display = isChecked ? 'block' : 'none';
};

window.renderFaqItems = (list) => {
    const container = document.getElementById('faqList');
    container.innerHTML = list.map((item, idx) => `
        <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:4px; border:1px solid #333;">
            <input type="text" placeholder="Question" class="faq-q" value="${item.q || ''}" style="margin-bottom:5px; font-weight:bold;">
            <textarea placeholder="Answer" class="faq-a" rows="2" style="margin-bottom:5px;">${item.a || ''}</textarea>
            <button class="btn-danger" style="padding:4px 8px; font-size:0.7rem;" onclick="removeFaqItem(${idx})">Remove</button>
        </div>
    `).join('');
};

window.addFaqItem = () => {
    saveCurrentFaqState(); // Save current inputs to memory
    const p = configData.pages.find(x => x.id === currentEditingPageId);
    p.schemas.faq_list.push({ q: "", a: "" });
    renderFaqItems(p.schemas.faq_list);
};

window.removeFaqItem = (idx) => {
    saveCurrentFaqState();
    const p = configData.pages.find(x => x.id === currentEditingPageId);
    p.schemas.faq_list.splice(idx, 1);
    renderFaqItems(p.schemas.faq_list);
};

// Helper to sync inputs back to data model before re-rendering
function saveCurrentFaqState() {
    if(!currentEditingPageId) return;
    const p = configData.pages.find(x => x.id === currentEditingPageId);
    const container = document.getElementById('faqList');
    if(!container) return;
    
    const qInputs = container.querySelectorAll('.faq-q');
    const aInputs = container.querySelectorAll('.faq-a');
    
    p.schemas.faq_list = Array.from(qInputs).map((input, idx) => ({
        q: input.value,
        a: aInputs[idx].value
    }));
}

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
    
    // Schema Saving
    saveCurrentFaqState(); // Ensure FAQs are synced
    
    if(!p.schemas) p.schemas = {};
    p.schemas.org = document.getElementById('schemaOrg').checked;
    p.schemas.website = document.getElementById('schemaWebsite').checked;
    p.schemas.faq = document.getElementById('schemaFaq').checked;
    // Live & Schedule are handled by Backend only now
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
