// ==========================================
// CONFIGURATION
// ==========================================
// REPLACE THIS with your specific repository details
const REPO_OWNER = 'arkhan66648'; 
const REPO_NAME = 'project1'; 
const FILE_PATH = 'data/config.json';
const BRANCH = 'main'; // or 'master'

// Global State
let currentSha = null; // Required by GitHub API to update files
let configData = {};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize TinyMCE
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
    if (!token) {
        document.getElementById('authModal').style.display = 'flex';
    } else {
        loadConfigFromGithub();
    }
});

// ==========================================
// GITHUB API FUNCTIONS
// ==========================================

async function loadConfigFromGithub() {
    const token = localStorage.getItem('gh_token');
    const statusMsg = document.getElementById('statusMsg');
    statusMsg.textContent = "⏳ Fetching data from GitHub...";

    try {
        const response = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`, {
            headers: {
                'Authorization': `token ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });

        if (!response.ok) throw new Error("Failed to fetch config.json");

        const data = await response.json();
        currentSha = data.sha; // Save SHA for later updates
        
        // Decode Base64 content
        const decodedContent = atob(data.content);
        configData = JSON.parse(decodedContent);

        populateUI(configData);
        statusMsg.textContent = "✅ Data loaded successfully";
        statusMsg.className = "status-ready"; // Add green color style if needed

    } catch (error) {
        console.error(error);
        statusMsg.textContent = "❌ Error loading data. Check console.";
        if(error.message.includes('404')) {
            alert("File data/config.json not found in repo! Please create it first.");
        }
    }
}

async function saveConfigToGithub() {
    const token = localStorage.getItem('gh_token');
    const statusMsg = document.getElementById('statusMsg');
    const saveBtn = document.getElementById('saveBtn');
    
    // UI Feedback
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
    statusMsg.textContent = "⏳ Committing changes to GitHub...";

    // 1. Gather Data from UI
    updateConfigFromUI();

    // 2. Convert to Base64
    const contentString = JSON.stringify(configData, null, 2);
    const contentEncoded = btoa(unescape(encodeURIComponent(contentString))); // Safe Unicode encoding

    try {
        const response = await fetch(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`, {
            method: 'PUT',
            headers: {
                'Authorization': `token ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: "CMS Update: Site Settings",
                content: contentEncoded,
                sha: currentSha, // Critical: Proves we are updating the latest version
                branch: BRANCH
            })
        });

        if (!response.ok) throw new Error("Failed to save to GitHub");

        const responseData = await response.json();
        currentSha = responseData.content.sha; // Update SHA for next save

        statusMsg.textContent = "✅ Saved! Site is rebuilding...";
        alert("Changes saved! The site will update in ~2 minutes.");

    } catch (error) {
        console.error(error);
        statusMsg.textContent = "❌ Save failed.";
        alert("Error saving. Check console for details.");
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "💾 Save Changes";
    }
}

// ==========================================
// UI <> DATA MAPPING
// ==========================================

function populateUI(data) {
    const s = data.site_settings;
    const api = data.api_keys;

    // General Settings
    document.getElementById('siteName').value = s.site_name || "";
    document.getElementById('siteDomain').value = s.domain || "";
    document.getElementById('logoUrl').value = s.logo_url || "";
    document.getElementById('faviconUrl').value = s.favicon || "";
    document.getElementById('homeH1').value = s.home_h1 || "";
    document.getElementById('metaTitle').value = s.meta_title || "";
    document.getElementById('metaDesc').value = s.meta_desc || "";
    document.getElementById('liveStatus').value = s.live_status_text || "Live and Working";

    // APIs
    document.getElementById('apiStreamed').value = api.streamed_url || "";
    document.getElementById('apiTopembed').value = api.topembed_url || "";

    // Sitelinks
    const container = document.getElementById('sitelinks-container');
    container.innerHTML = ''; // Clear existing
    if (data.site_links) {
        data.site_links.forEach(link => addSitelinkUI(link));
    }
    
    updatePageSelector();
}

function updateConfigFromUI() {
    // Site Settings
    configData.site_settings = {
        site_name: document.getElementById('siteName').value,
        domain: document.getElementById('siteDomain').value,
        logo_url: document.getElementById('logoUrl').value,
        favicon: document.getElementById('faviconUrl').value,
        home_h1: document.getElementById('homeH1').value,
        meta_title: document.getElementById('metaTitle').value,
        meta_desc: document.getElementById('metaDesc').value,
        live_status_text: document.getElementById('liveStatus').value
    };

    // APIs
    configData.api_keys = {
        streamed_url: document.getElementById('apiStreamed').value,
        topembed_url: document.getElementById('apiTopembed').value
    };

    // Sitelinks
    const links = [];
    document.querySelectorAll('.sitelink-item').forEach(item => {
        links.push({
            id: parseInt(item.dataset.id),
            title: item.querySelector('.link-title').value,
            slug: item.querySelector('.link-slug').value,
            priority: parseInt(item.querySelector('.link-priority').value),
            meta_title: item.querySelector('.link-meta-title').value,
            meta_desc: item.querySelector('.link-meta-desc').value
        });
    });
    configData.site_links = links;
}

// ==========================================
// SITELINK MANAGER (Updated for Real Data)
// ==========================================

function addSitelinkUI(data = null) {
    const container = document.getElementById('sitelinks-container');
    const id = data ? data.id : Date.now(); 
    
    const link = data || { title: "", slug: "", priority: 1, meta_title: "", meta_desc: "" };

    const html = `
    <div class="sitelink-item" data-id="${id}" id="link-${id}">
        <button class="btn-delete" onclick="removeSitelink('${id}')">🗑 Remove</button>
        <div class="sitelink-header">
            <div style="flex: 2;">
                <label>Link Title</label>
                <input type="text" class="link-title" value="${link.title}">
            </div>
            <div style="flex: 2;">
                <label>Slug (e.g., nfl)</label>
                <input type="text" class="link-slug" value="${link.slug}">
            </div>
            <div style="flex: 1;">
                <label>Priority</label>
                <input type="number" class="link-priority" value="${link.priority}">
            </div>
        </div>
        <div class="sitelink-meta">
            <div>
                <label>Page Meta Title</label>
                <input type="text" class="link-meta-title" value="${link.meta_title}">
            </div>
            <div>
                <label>Page Meta Description</label>
                <input type="text" class="link-meta-desc" value="${link.meta_desc}">
            </div>
        </div>
    </div>
    `;
    
    container.insertAdjacentHTML('beforeend', html);
    updatePageSelector();
}

function removeSitelink(id) {
    if(confirm("Delete this link? This will remove the page on next update.")) {
        document.getElementById(`link-${id}`).remove();
        updatePageSelector();
    }
}

function updatePageSelector() {
    const selector = document.getElementById('pageSelector');
    selector.innerHTML = '<option value="home">Homepage (Main)</option>';
    document.querySelectorAll('.sitelink-item').forEach(item => {
        const title = item.querySelector('.link-title').value;
        const slug = item.querySelector('.link-slug').value;
        if(title) {
            const opt = document.createElement('option');
            opt.value = slug;
            opt.innerText = `Page: ${title} (${slug})`;
            selector.appendChild(opt);
        }
    });
}

// Helpers
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).classList.add('active');
    
    // Simple visual toggle logic
    if(tabId === 'settings') document.querySelectorAll('.nav-btn')[0].classList.add('active');
    if(tabId === 'sitelinks') document.querySelectorAll('.nav-btn')[1].classList.add('active');
    if(tabId === 'article') document.querySelectorAll('.nav-btn')[2].classList.add('active');
}

function saveToken() {
    const token = document.getElementById('ghToken').value;
    if (token) {
        localStorage.setItem('gh_token', token);
        document.getElementById('authModal').style.display = 'none';
        loadConfigFromGithub();
    }
}

document.getElementById('saveBtn').addEventListener('click', saveConfigToGithub);
