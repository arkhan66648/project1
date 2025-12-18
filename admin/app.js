// ==========================================
// CONFIGURATION: UPDATE THESE!
// ==========================================
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1'; 
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; 

// State
let currentSha = null;
let configData = {};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Init TinyMCE
    tinymce.init({
        selector: '#tinymce-editor',
        height: 500,
        plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount',
        toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap | removeformat',
        skin: "oxide-dark",
        content_css: "dark"
    });

    // 2. Check Auth
    const token = localStorage.getItem('gh_token');
    if (!token) document.getElementById('authModal').style.display = 'flex';
    else loadConfig();
});

// ==========================================
// GITHUB API
// ==========================================
async function loadConfig() {
    const token = localStorage.getItem('gh_token');
    const msg = document.getElementById('statusMsg');
    msg.textContent = "⏳ Loading...";

    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: { 'Authorization': `token ${token}`, 'Accept': 'application/vnd.github.v3+json' }
        });

        if (!res.ok) throw new Error("Load failed");
        
        const data = await res.json();
        currentSha = data.sha;
        configData = JSON.parse(atob(data.content));

        populateUI(configData);
        msg.textContent = "✅ Ready";

    } catch (err) {
        console.error(err);
        msg.textContent = "❌ Error";
        if(err.message.includes('404')) alert("Config file not found in repo.");
    }
}

async function saveConfig() {
    const token = localStorage.getItem('gh_token');
    const btn = document.getElementById('saveBtn');
    const msg = document.getElementById('statusMsg');
    
    btn.disabled = true;
    msg.textContent = "⏳ Saving...";

    updateDataFromUI();

    const content = btoa(unescape(encodeURIComponent(JSON.stringify(configData, null, 2))));

    try {
        const res = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: {
                'Authorization': `token ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: "Admin: Config Update",
                content: content,
                sha: currentSha,
                branch: BRANCH
            })
        });

        if (!res.ok) throw new Error("Save failed");
        
        const data = await res.json();
        currentSha = data.content.sha;
        msg.textContent = "✅ Saved!";
        alert("Settings saved successfully.");

    } catch (err) {
        console.error(err);
        msg.textContent = "❌ Save Failed";
        alert("Error saving to GitHub. Check console.");
    } finally {
        btn.disabled = false;
    }
}

// ==========================================
// UI HANDLING
// ==========================================
function populateUI(data) {
    const s = data.site_settings || {};
    const t = data.theme || {};
    const api = data.api_keys || {};

    // Settings
    setVal('siteName', s.site_name);
    setVal('siteDomain', s.domain);
    setVal('logoUrl', s.logo_url);
    setVal('metaTitle', s.meta_title);
    setVal('metaDesc', s.meta_desc);
    setVal('apiStreamed', api.streamed_url);
    setVal('apiTopembed', api.topembed_url);

    // Theme Mappings
    setColor('themeAccent', 'txtAccent', t.color_accent || '#D00000');
    setColor('themeDark', 'txtDark', t.brand_dark || '#8a0000');
    setColor('themeLive', 'txtLive', t.color_live || '#00e676');
    setColor('themeGold', 'txtGold', t.color_gold || '#FFD700');

    // Sitelinks
    const container = document.getElementById('sitelinks-container');
    container.innerHTML = '';
    (data.site_links || []).forEach(link => addSitelinkUI(link));
    
    updatePageSelector();
}

function updateDataFromUI() {
    configData.site_settings = {
        site_name: getVal('siteName'),
        domain: getVal('siteDomain'),
        logo_url: getVal('logoUrl'),
        meta_title: getVal('metaTitle'),
        meta_desc: getVal('metaDesc')
    };

    configData.theme = {
        color_accent: getVal('themeAccent'),
        brand_dark: getVal('themeDark'),
        color_live: getVal('themeLive'),
        color_gold: getVal('themeGold')
    };

    configData.api_keys = {
        streamed_url: getVal('apiStreamed'),
        topembed_url: getVal('apiTopembed')
    };

    // Sitelinks
    const links = [];
    document.querySelectorAll('.sitelink-item').forEach(item => {
        links.push({
            id: parseInt(item.dataset.id),
            title: item.querySelector('.lnk-title').value,
            slug: item.querySelector('.lnk-slug').value,
            priority: parseInt(item.querySelector('.lnk-priority').value),
            meta_title: item.querySelector('.lnk-meta-title').value,
            meta_desc: item.querySelector('.lnk-meta-desc').value
        });
    });
    configData.site_links = links;
}

// ==========================================
// SITELINKS MANAGER
// ==========================================
function addSitelinkUI(data = null) {
    const id = data ? data.id : Date.now();
    const link = data || { title: "", slug: "", priority: 1, meta_title: "", meta_desc: "" };
    
    const html = `
    <div class="sitelink-item" data-id="${id}" id="lnk-${id}">
        <button class="btn-delete" onclick="removeLink('${id}')">🗑</button>
        <div class="sitelink-header">
            <div style="flex:2"><label>Title</label><input type="text" class="lnk-title" value="${link.title}"></div>
            <div style="flex:2"><label>Slug (e.g. nfl)</label><input type="text" class="lnk-slug" value="${link.slug}"></div>
            <div style="flex:1"><label>Priority</label><input type="number" class="lnk-priority" value="${link.priority}"></div>
        </div>
        <div class="sitelink-header">
            <div style="flex:1"><label>Meta Title</label><input type="text" class="lnk-meta-title" value="${link.meta_title}"></div>
            <div style="flex:1"><label>Meta Desc</label><input type="text" class="lnk-meta-desc" value="${link.meta_desc}"></div>
        </div>
    </div>`;
    document.getElementById('sitelinks-container').insertAdjacentHTML('beforeend', html);
    updatePageSelector();
}

function removeLink(id) {
    if(confirm("Delete page?")) {
        document.getElementById(`lnk-${id}`).remove();
        updatePageSelector();
    }
}

// ==========================================
// HELPERS
// ==========================================
function setVal(id, val) { if(document.getElementById(id)) document.getElementById(id).value = val || ""; }
function getVal(id) { return document.getElementById(id).value; }

function setColor(colorId, textId, val) {
    setVal(colorId, val);
    setVal(textId, val);
    // Sync listener attached in HTML inline for brevity, but better here:
    document.getElementById(colorId).addEventListener('input', e => document.getElementById(textId).value = e.target.value);
    document.getElementById(textId).addEventListener('input', e => document.getElementById(colorId).value = e.target.value);
}

function syncColor(input, targetId) { document.getElementById(targetId).value = input.value; }

function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
    document.getElementById(`tab-${id}`).classList.add('active');
    event.target.classList.add('active');
}

function updatePageSelector() {
    const sel = document.getElementById('pageSelector');
    sel.innerHTML = '<option value="home">Homepage</option>';
    document.querySelectorAll('.sitelink-item').forEach(i => {
        const title = i.querySelector('.lnk-title').value;
        if(title) {
            const opt = document.createElement('option');
            opt.innerText = title;
            sel.appendChild(opt);
        }
    });
}

function saveToken() {
    const t = document.getElementById('ghToken').value;
    if(t) {
        localStorage.setItem('gh_token', t);
        document.getElementById('authModal').style.display = 'none';
        loadConfig();
    }
}

document.getElementById('saveBtn').addEventListener('click', saveConfig);
