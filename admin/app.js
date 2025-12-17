// Global Config State (Will be populated from GitHub later)
let siteConfig = {
    site_links: []
};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize TinyMCE
    tinymce.init({
        selector: '#tinymce-editor',
        height: 500,
        plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount',
        toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap | removeformat',
        skin: "oxide-dark",
        content_css: "dark",
        setup: (editor) => {
            editor.on('change', () => {
                // Auto-save logic can go here later
            });
        }
    });

    // 2. Check Authentication
    const token = localStorage.getItem('gh_token');
    if (!token) {
        document.getElementById('authModal').style.display = 'flex';
    }

    // 3. Mock Data Load (Simulating what we will fetch from config.json)
    // We will replace this with real GitHub fetching in Phase 2
    mockLoadConfig();
});

// --- UI FUNCTIONS ---

function switchTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    
    // Show target
    document.getElementById(`tab-${tabId}`).classList.add('active');
    
    // Highlight button (find button that called this, roughly)
    const buttons = document.querySelectorAll('.nav-btn');
    if(tabId === 'settings') buttons[0].classList.add('active');
    if(tabId === 'sitelinks') buttons[1].classList.add('active');
    if(tabId === 'article') buttons[2].classList.add('active');
}

function saveToken() {
    const token = document.getElementById('ghToken').value;
    if (token.startsWith('ghp_') || token.startsWith('github_pat_')) {
        localStorage.setItem('gh_token', token);
        document.getElementById('authModal').style.display = 'none';
        alert("Authenticated! Ready to manage site.");
    } else {
        alert("Invalid Token format.");
    }
}

// --- SITELINKS MANAGER ---

function addSitelinkUI(data = null) {
    const container = document.getElementById('sitelinks-container');
    const id = Date.now(); // Unique ID for DOM
    
    // Default empty values if creating new
    const link = data || { title: "", slug: "", priority: 1, meta_title: "", meta_desc: "" };

    const html = `
    <div class="sitelink-item" id="link-${id}">
        <button class="btn-delete" onclick="removeSitelink('${id}')">🗑 Remove</button>
        <div class="sitelink-header">
            <div style="flex: 2;">
                <label>Link Title (Menu Name)</label>
                <input type="text" class="link-title" value="${link.title}" placeholder="e.g. NFL">
            </div>
            <div style="flex: 2;">
                <label>URL Slug (Page Name)</label>
                <input type="text" class="link-slug" value="${link.slug}" placeholder="e.g. /nfl">
            </div>
            <div style="flex: 1;">
                <label>Priority</label>
                <input type="number" class="link-priority" value="${link.priority}">
            </div>
        </div>
        <div class="sitelink-meta">
            <div>
                <label>Page Meta Title</label>
                <input type="text" class="link-meta-title" value="${link.meta_title}" placeholder="SEO Title for this page">
            </div>
            <div>
                <label>Page Meta Description</label>
                <input type="text" class="link-meta-desc" value="${link.meta_desc}" placeholder="SEO Description">
            </div>
        </div>
    </div>
    `;
    
    container.insertAdjacentHTML('beforeend', html);
    updatePageSelector();
}

function removeSitelink(id) {
    if(confirm("Are you sure? This will delete the page on the next build.")) {
        document.getElementById(`link-${id}`).remove();
        updatePageSelector();
    }
}

function updatePageSelector() {
    const selector = document.getElementById('pageSelector');
    // Keep first option (Homepage)
    selector.innerHTML = '<option value="home">Homepage (Main)</option>';
    
    // Scan current inputs
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

// --- MOCK DATA LOADING (For Phase 1 Testing) ---
function mockLoadConfig() {
    // Simulating existing data
    document.getElementById('siteName').value = "StreamEast US";
    document.getElementById('siteDomain').value = "streameast.app";
    
    // Add one sample link
    addSitelinkUI({
        title: "NFL",
        slug: "nfl",
        priority: 1,
        meta_title: "Watch NFL Live Stream Free",
        meta_desc: "The best place to watch NFL games online."
    });
}

document.getElementById('saveBtn').addEventListener('click', () => {
    alert("This will connect to GitHub API in Phase 2!");
});
