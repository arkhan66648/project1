// Global State
let allMatches = [];
let countdownInterval;
const CFG = window.SITE_CONFIG || {};

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    await loadMatches();
    startCountdowns();
    
    // Search Listener
    const searchInput = document.getElementById('match-search');
    if (searchInput) searchInput.addEventListener('input', (e) => handleSearch(e.target.value));
}

async function loadMatches() {
    try {
        const res = await fetch('data/matches.json?t=' + Date.now());
        const data = await res.json();
        allMatches = data;

        // 1. Render Trending (Top 5 + Rest)
        renderTrending(data.trending);

        // 2. Render Wildcard (Home Only)
        if (CFG.isHome && CFG.wildcard && CFG.wildcard.category) {
            renderWildcard(data.wildcard_matches);
        }

        // 3. Render Upcoming Categories
        if (CFG.pageType === 'schedule') {
            renderUpcoming(data.categories, data.all_matches); // Pass all_matches for category page filtering
        }

        // Update Online Count
        const countEl = document.getElementById('onlineCount');
        if (countEl) {
            const liveCount = data.trending.filter(m => m.is_live).length;
            countEl.innerText = `● ${liveCount} Matches Online`;
            countEl.style.color = liveCount > 0 ? 'var(--brand-primary)' : '#888';
        }

    } catch (err) { console.error("Error loading matches:", err); }
}

// ==============================================
// RENDER LOGIC
// ==============================================

function renderTrending(matches) {
    const container = document.getElementById('live-matches-container');
    const btnMore = document.getElementById('btnShowMore');
    if(!container) return;

    if (matches.length === 0) {
        container.innerHTML = `<div style="padding:20px;text-align:center;color:#666">No matches right now.</div>`;
        return;
    }

    matches.forEach((match, index) => {
        const row = createMatchRow(match);
        if (index >= 5) row.classList.add('hidden-trend', 'hidden'); // Initially hide > 5
        container.appendChild(row);
    });

    // View Rest Logic
    if (matches.length > 5 && btnMore) {
        btnMore.style.display = 'inline-block';
        btnMore.textContent = `Show ${matches.length - 5} More Matches ▼`;
        btnMore.onclick = () => {
            document.querySelectorAll('.hidden-trend').forEach(el => el.classList.remove('hidden'));
            btnMore.style.display = 'none';
        };
    }
}

function renderWildcard(matches) {
    const wrapper = document.getElementById('wildcard-wrapper');
    if (!wrapper) return;

    const catName = CFG.wildcard.category;
    const sectionId = CFG.wildcard.id || 'wildcard';
    
    // Header
    let html = `
        <div class="sec-head" id="${sectionId}">
            <div class="sec-title">🔥 Upcoming ${catName}</div>
        </div>
        <div class="match-list">
    `;

    if (matches.length === 0) {
        // Fallback Entity Text
        html += `<p class="entity-intro" style="text-align:center; margin:20px;">${CFG.wildcard.fallback || 'No upcoming matches found.'}</p>`;
    } else {
        wrapper.innerHTML = html + '</div>'; // Temp close to append elements
        const list = wrapper.querySelector('.match-list');
        matches.forEach(m => list.appendChild(createMatchRow(m)));
        return;
    }
    wrapper.innerHTML = html + '</div>';
}

function renderUpcoming(categories, allData) {
    const wrapper = document.getElementById('upcoming-wrapper');
    if (!wrapper) return;

    // If Category Page, filter only that category
    if (!CFG.isHome && CFG.category) {
        const catName = CFG.category.toLowerCase();
        // Try exact match in categories OR filter all data
        const catMatches = categories[Object.keys(categories).find(k=>k.toLowerCase()===catName)] || 
                           allData.filter(m => m.sport.toLowerCase() === catName || m.league.toLowerCase() === catName);
        
        wrapper.innerHTML = `<div class="sec-head"><div class="sec-title">${CFG.category} Schedule</div></div><div class="match-list" id="cat-list"></div>`;
        const list = wrapper.querySelector('#cat-list');
        
        if(catMatches.length === 0) list.innerHTML = `<div style="padding:20px;text-align:center">No scheduled matches.</div>`;
        else catMatches.forEach(m => list.appendChild(createMatchRow(m)));
        return;
    }

    // Home Page: Loop Categories (excluding Wildcard if duplicate check needed, but Python handles that)
    Object.keys(categories).forEach(sport => {
        const matches = categories[sport];
        if (matches.length > 0) {
            const sec = document.createElement('div');
            sec.className = 'sport-section';
            sec.dataset.sport = sport.toLowerCase();
            sec.innerHTML = `
                <div class="sec-head">
                    <div class="sec-title">${getIcon(sport)} Upcoming ${sport}</div>
                    <a href="/${sport.toLowerCase().replace(/ /g,'-')}/" class="sec-right-link">View All ></a>
                </div>
                <div class="match-list"></div>
            `;
            const list = sec.querySelector('.match-list');
            // Limit to 4 for Home
            matches.slice(0, 4).forEach(m => list.appendChild(createMatchRow(m)));
            wrapper.appendChild(sec);
        }
    });
}

// ==============================================
// MATCH ROW GENERATOR (3-COLUMN LAYOUT)
// ==============================================
function createMatchRow(match) {
    const div = document.createElement('div');
    div.className = match.is_live ? 'match-row live' : 'match-row';
    div.dataset.search = (match.title + " " + match.league).toLowerCase();

    // COL 1: Time/Date OR Live/Runtime
    let col1 = '';
    if (match.is_live) {
        // "34'" or "HT" from backend
        const runtime = match.running_time || "LIVE"; 
        col1 = `<span class="live-txt">LIVE</span><span class="time-sub" style="color:#fff">${runtime}</span>`;
    } else {
        // Compact: "7:30 PM" \n "Oct 12"
        col1 = `<span class="time-main">${match.fmt_time.split(' ')[0]} <small>${match.fmt_time.split(' ')[1]}</small></span>
                <span class="time-sub">${match.fmt_date}</span>`;
    }

    // COL 2: Teams
    let col2 = '';
    const teams = match.teams_ui || [];
    if(teams.length > 0) {
        col2 += `<div class="team-name"><span class="t-circle" style="background:${teams[0].color}">${teams[0].letter}</span>${teams[0].name}</div>`;
        if(teams[1]) col2 += `<div class="team-name"><span class="t-circle" style="background:${teams[1].color}">${teams[1].letter}</span>${teams[1].name}</div>`;
    } else {
        col2 = `<div class="team-name">${match.title}</div>`;
    }
    col2 = `<div class="league-tag">${match.league}</div>` + col2;

    // COL 3: Meta/Button
    let col3 = '';
    if (match.show_button) {
        // Viewer Emoji Logic
        const v = match.viewers || 0;
        let icon = '⚡'; 
        if(v > 1000) icon = '📈';
        if(v > 10000) icon = '🔥';
        if(v > 50000) icon = '👁️';

        const meta = match.is_live ? `${icon} ${kFormatter(v)}` : `HD`;
        col3 = `<div class="meta-top">${meta}</div>
                <button class="btn-watch" onclick="openPlayer('${match.id}', '${match.streams[0]?.id}', '${match.title.replace(/'/g,"")}')">WATCH</button>`;
    } else {
        // Countdown
        col3 = `<div class="meta-top"><span class="countdown" data-time="${match.start_time}">--:--</span></div>
                <button class="btn-watch btn-notify" onclick="toggleNotify(this)">🔔 Notify</button>`;
    }

    div.innerHTML = `
        <div class="col-time">${col1}</div>
        <div class="col-info">${col2}</div>
        <div class="col-meta">${col3}</div>
    `;
    return div;
}

// ==============================================
// UTILITIES
// ==============================================
function kFormatter(num) {
    return Math.abs(num) > 999 ? Math.sign(num)*((Math.abs(num)/1000).toFixed(1)) + 'k' : Math.sign(num)*Math.abs(num);
}

function getIcon(sport) {
    const map = { "NBA":"🏀", "NFL":"🏈", "UFC":"🥊", "Soccer":"⚽", "MLB":"⚾", "F1":"🏎️", "Tennis":"🎾", "Boxing":"🥊" };
    return map[sport] || "🏆";
}

function startCountdowns() {
    setInterval(() => {
        document.querySelectorAll('.countdown').forEach(el => {
            const t = parseInt(el.dataset.time);
            const diff = t - Date.now();
            if(diff <= 0) { el.innerText = "SOON"; return; }
            const h = Math.floor(diff/3600000);
            const m = Math.floor((diff%3600000)/60000);
            el.innerText = h > 24 ? "1d+" : `${h}h ${m}m`;
        });
    }, 60000);
}

function toggleNotify(btn) {
    if(btn.innerText.includes("Notify")) {
        btn.innerText = "✅ Set"; btn.classList.add('set');
    } else {
        btn.innerText = "🔔 Notify"; btn.classList.remove('set');
    }
}

// Player Logic
function openPlayer(mid, sid, title) {
    const modal = document.getElementById('vModal');
    const ctr = document.getElementById('vContainer');
    document.getElementById('vmTitle').innerText = title;
    
    // Decode Base64
    let url = "";
    try { url = atob(sid); } catch(e){}
    
    ctr.innerHTML = `<iframe src="${url}" allow="autoplay; fullscreen" allowfullscreen></iframe>`;
    modal.style.display = 'flex';
}

function closeStream() {
    document.getElementById('vModal').style.display = 'none';
    document.getElementById('vContainer').innerHTML = '';
}

// Search
function handleSearch(term) {
    const clean = term.toLowerCase();
    document.getElementById('searchClear').style.display = clean ? 'flex' : 'none';
    
    document.querySelectorAll('.match-row').forEach(row => {
        const txt = row.dataset.search;
        row.style.display = txt.includes(clean) ? 'grid' : 'none';
    });
    
    // Hide empty sections
    document.querySelectorAll('.sport-section').forEach(sec => {
        const vis = sec.querySelectorAll('.match-row[style="display: grid;"]').length;
        sec.style.display = vis > 0 ? 'block' : 'none';
    });
}
function clearSearch() { document.getElementById('match-search').value = ''; handleSearch(''); }

// Social Sharing
function shareSite(platform) {
    const url = encodeURIComponent(window.location.origin);
    const text = encodeURIComponent(`Watch Live Sports Free on ${CFG.siteName}!`);
    let link = "";
    if(platform === 'twitter') link = `https://twitter.com/intent/tweet?url=${url}&text=${text}`;
    if(platform === 'telegram') link = `https://t.me/share/url?url=${url}&text=${text}`;
    if(link) window.open(link, '_blank');
}

function copyLink() {
    navigator.clipboard.writeText(window.location.origin).then(() => {
        alert("Link copied to clipboard!");
    });
}
