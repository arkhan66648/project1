document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

// Detect Path (Root vs Subfolder)
const BASE_PATH = window.IS_SUBPAGE ? '../' : './';
const DATA_URL = `${BASE_PATH}data/matches.json`;
const CONFIG_URL = `${BASE_PATH}data/config.json`;

async function initApp() {
    await loadConfig();
    await loadMatches();
    setupSearch();
    handleHistoryNav();
}

// ==============================================
// 1. CONFIG & THEME ENGINE
// ==============================================
async function loadConfig() {
    try {
        const res = await fetch(CONFIG_URL);
        const config = await res.json();
        
        // A. Apply Theme (CSS Variables)
        if (config.theme) {
            const root = document.documentElement;
            const map = {
                'bg_body': '--bg-body', 'bg_card': '--bg-card', 'bg_header': '--bg-header',
                'text_main': '--text-main', 'text_muted': '--text-muted',
                'color_accent': '--accent', 'color_live': '--live', 'border_radius': '--radius'
            };
            Object.keys(map).forEach(key => {
                if(config.theme[key]) root.style.setProperty(map[key], config.theme[key]);
            });
        }

        // B. Update Text & Identity
        const s = config.site_settings;
        if (!window.IS_SUBPAGE) {
            if(s.home_h1) document.getElementById('hero-title').textContent = s.home_h1;
            if(s.live_status_text) document.getElementById('status-text').textContent = s.live_status_text;
            document.title = s.meta_title || document.title;
        }
        
        const logoLinks = document.querySelectorAll('.logo a');
        logoLinks.forEach(l => l.innerText = s.site_name || "StreamRank");

        // C. Build Navigation
        const nav = document.getElementById('site-links-nav');
        if(nav) {
            nav.innerHTML = '';
            // Home Link
            const home = document.createElement('a');
            home.href = `${BASE_PATH}index.html`;
            home.textContent = "Home";
            nav.appendChild(home);

            // Dynamic Links
            config.site_links.forEach(link => {
                const a = document.createElement('a');
                // Clean slug and build path
                const slug = link.slug.replace(/^\/|\/$/g, '');
                a.href = `${BASE_PATH}${slug}/index.html`;
                a.textContent = link.title;
                nav.appendChild(a);
            });
        }

    } catch (err) {
        console.error("Config Error:", err);
    }
}

// ==============================================
// 2. MATCH LOADING
// ==============================================
async function loadMatches() {
    try {
        // Fetch with timestamp to prevent caching
        const res = await fetch(DATA_URL + '?t=' + Date.now());
        const data = await res.json();

        // A. Inject Schema (Homepage Only)
        if(!window.IS_SUBPAGE && data.home_schema) {
            const script = document.createElement('script');
            script.type = 'application/ld+json';
            script.textContent = JSON.stringify(data.home_schema);
            document.head.appendChild(script);
        }

        // B. Render Important (Homepage)
        if (!window.IS_SUBPAGE) {
            renderTable(data.important, 'table-important', true);
        }

        // C. Render Categories
        if (window.IS_SUBPAGE) {
            // Subpage Mode
            const catMatches = data.categories[window.PAGE_CATEGORY] || [];
            const tbody = document.getElementById('category-matches-body');
            if(tbody) {
                tbody.innerHTML = '';
                if(catMatches.length === 0) tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:2rem; color:var(--text-muted)">No active matches found.</td></tr>`;
                else catMatches.forEach(m => tbody.appendChild(createMatchRow(m)));
            }
        } else {
            // Homepage Mode (Stack Categories)
            const wrapper = document.getElementById('category-wrapper');
            const priority = ["NFL", "NBA", "UFC", "NHL", "MLB", "Soccer", "F1"];
            const cats = Object.keys(data.categories).sort((a,b) => {
                return (priority.indexOf(a) > -1 ? priority.indexOf(a) : 99) - (priority.indexOf(b) > -1 ? priority.indexOf(b) : 99);
            });

            cats.forEach(cat => {
                const matches = data.categories[cat];
                if(matches.length > 0) {
                    const section = document.createElement('section');
                    section.className = 'match-section';
                    section.innerHTML = `<h2>${cat}</h2><table class="match-table"><thead><tr><th class="col-time">Time</th><th class="col-match">Match</th><th class="col-action">Action</th></tr></thead><tbody id="tbody-${cat}"></tbody></table>`;
                    wrapper.appendChild(section);
                    matches.forEach(m => document.getElementById(`tbody-${cat}`).appendChild(createMatchRow(m)));
                }
            });
        }
    } catch (err) {
        console.error("Match Error:", err);
    }
}

function renderTable(matches, id, isHero) {
    const el = document.getElementById(id);
    if(!el) return;
    if(matches.length === 0 && isHero) {
        document.getElementById('section-important').style.display = 'none';
        return;
    }
    el.innerHTML = '';
    matches.forEach(m => el.appendChild(createMatchRow(m)));
}

// ==============================================
// 3. ROW & BUTTON GENERATOR
// ==============================================
function createMatchRow(match) {
    const tr = document.createElement('tr');
    tr.className = 'match-row';
    tr.dataset.search = (match.title + " " + match.sport).toLowerCase();

    // Time Logic
    const date = new Date(match.start_time);
    let timeHtml = match.is_live 
        ? `<span style="color:var(--live); font-weight:bold;">● LIVE</span>`
        : `${date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}<br><span style="font-size:0.75rem; opacity:0.6">${date.toLocaleDateString([], {month:'short', day:'numeric'})}</span>`;

    // Title Logic
    const titleHtml = `<span class="match-title">${match.title}</span><span class="match-league">${match.sport}</span>`;

    // Button Logic (CLOAKING)
    // We grab the first stream encoded ID.
    let btnHtml = '<span style="opacity:0.5; font-size:0.8rem">Upcoming</span>';
    
    if (match.show_button && match.streams && match.streams.length > 0) {
        // Use the first stream for the main button
        const encodedLink = match.streams[0].id; 
        const safeTitle = match.title.replace(/'/g, "").replace(/"/g, "");
        
        btnHtml = `<button class="btn-watch" onclick="openPlayer('${match.id}', '${encodedLink}', '${safeTitle}')">Watch Now</button>`;
    }

    tr.innerHTML = `<td class="col-time">${timeHtml}</td><td>${titleHtml}</td><td class="col-action">${btnHtml}</td>`;
    return tr;
}

// ==============================================
// 4. OVERLAY & URL CLOAKING
// ==============================================
function openPlayer(id, encodedUrl, title) {
    const overlay = document.getElementById('stream-overlay');
    const box = document.getElementById('player-box');
    const titleSpan = document.getElementById('overlay-title');

    // A. Decode Base64
    let url = "";
    try { url = atob(encodedUrl); } 
    catch(e) { alert("Stream Link Error"); return; }

    // B. Embed
    box.innerHTML = `<iframe src="${url}" allowfullscreen scrolling="no" allow="encrypted-media; autoplay"></iframe>`;
    titleSpan.textContent = "Watching: " + title;

    // C. Show
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    // D. Cloak URL (Change browser URL to ?watch=ID without reloading)
    // This tricks users/agents into thinking they are on a specific page
    const fakeState = { isPlayer: true, id: id };
    history.pushState(fakeState, title, `?watch=${id}`);
}

function closePlayer() {
    const overlay = document.getElementById('stream-overlay');
    const box = document.getElementById('player-box');

    overlay.classList.remove('active');
    document.body.style.overflow = '';
    box.innerHTML = ''; // Kill Iframe

    // Revert URL
    if (history.state && history.state.isPlayer) {
        history.back();
    }
}

function handleHistoryNav() {
    window.addEventListener('popstate', (e) => {
        // If user presses Back button and overlay is open, close it
        const overlay = document.getElementById('stream-overlay');
        if (overlay.classList.contains('active')) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
            document.getElementById('player-box').innerHTML = '';
        }
    });
}

// ==============================================
// 5. SEARCH
// ==============================================
function setupSearch() {
    const input = document.getElementById('match-search');
    if(!input) return;

    input.addEventListener('keyup', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.match-row').forEach(row => {
            row.classList.toggle('hidden', !row.dataset.search.includes(term));
        });
        
        // Hide empty tables
        document.querySelectorAll('.match-table').forEach(table => {
            const hasVisible = table.querySelectorAll('tbody tr:not(.hidden)').length > 0;
            table.closest('.match-section').style.display = hasVisible ? 'block' : 'none';
        });
    });
}
