document.addEventListener("DOMContentLoaded", () => {
    loadMatches();
    setupSearch();
});

async function loadMatches() {
    try {
        const res = await fetch('data/matches.json?t=' + Date.now());
        const data = await res.json();
        
        const liveContainer = document.getElementById('live-matches-container');
        const upcomingWrapper = document.getElementById('upcoming-wrapper');
        
        if(liveContainer) liveContainer.innerHTML = '';
        if(upcomingWrapper) upcomingWrapper.innerHTML = '';

        // 1. TRENDING (Show top 6, hide rest)
        const trending = data.important;
        trending.forEach((match, index) => {
            const row = createGridRow(match);
            if(index >= 6) row.classList.add('hidden-trend'); // Hide extra
            if(liveContainer) liveContainer.appendChild(row);
        });
        
        // Show More Button Logic
        if(trending.length > 6) {
            const btn = document.getElementById('btnShowMore');
            btn.style.display = 'inline-block';
            btn.textContent = `Show ${trending.length - 6} More Matches ▼`;
        }

        // 2. UPCOMING SECTIONS (Sorted by USA Popularity)
        const priorityOrder = ["NFL", "NBA", "UFC", "MLB", "NHL", "Soccer", "F1", "Boxing"];
        // Sort keys based on priority
        const sortedKeys = Object.keys(data.categories).sort((a, b) => {
            let idxA = priorityOrder.indexOf(a); let idxB = priorityOrder.indexOf(b);
            if (idxA === -1) idxA = 99; if (idxB === -1) idxB = 99;
            return idxA - idxB;
        });

        sortedKeys.forEach(sport => {
            const matches = data.categories[sport].filter(m => !m.is_live); // Only upcoming
            if(matches.length > 0) {
                // Create Section Header
                const sec = document.createElement('div');
                sec.innerHTML = `
                    <div class="sec-head">
                        <div class="sec-title">${getSportIcon(sport)} Upcoming ${sport}</div>
                        <a href="/${sport.toLowerCase()}/" class="sec-right-link">View Schedule ></a>
                    </div>
                    <div class="match-list" id="list-${sport}"></div>
                `;
                upcomingWrapper.appendChild(sec);
                
                // Add Matches (Limit 4 for Home)
                const listDiv = document.getElementById(`list-${sport}`);
                matches.slice(0, 4).forEach(m => listDiv.appendChild(createGridRow(m)));
            }
        });

    } catch (err) { console.error(err); }
}

function createGridRow(match) {
    const div = document.createElement('div');
    div.className = match.is_live ? 'match-row live' : 'match-row';
    div.dataset.search = (match.title + " " + match.sport).toLowerCase();

    // Time
    const d = new Date(match.start_time);
    const timeStr = match.is_live 
        ? `<span class="live-txt">LIVE</span>` 
        : `<span class="time-main">${d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>`;

    // Visuals Logic
    let metaHtml = '';
    if(match.is_live) {
        const v = match.viewers || 0;
        let icon = '⚡ Stable';
        if(v > 10000) icon = `🔥 ${kFormatter(v)}`;
        else if(v > 1000) icon = `📈 ${kFormatter(v)}`;
        
        metaHtml = `<div class="meta-top">${icon}</div><div class="meta-bot">HD</div>`;
    } else {
        metaHtml = `<div class="meta-top" style="color:#888">⏳</div><div class="meta-bot">HD</div>`;
    }

    // Teams
    let parts = match.title.split(' vs ');
    if(parts.length < 2) parts = match.title.split(' - ');
    const t1 = parts[0] || match.title;
    const t2 = parts[1] || "";

    // Button
    let btnHtml = `<button class="btn-watch btn-notify">🔔 Notify</button>`;
    if(match.show_button) {
        const id = match.streams[0]?.id || "";
        const title = match.title.replace(/'/g, "");
        btnHtml = `<button class="btn-watch" onclick="openPlayer('${match.id}', '${id}', '${title}')">WATCH</button>`;
    }

    div.innerHTML = `
        <div class="col-time">${timeStr}<span class="time-sub">${d.toLocaleDateString([],{month:'short',day:'numeric'})}</span></div>
        <div class="col-info">
            <div class="league-tag">${match.sport}</div>
            <div class="team-name"><span class="team-dot"></span> ${t1}</div>
            <div class="team-name"><span class="team-dot"></span> ${t2}</div>
        </div>
        <div class="col-meta">${metaHtml}</div>
        <div class="col-action">${btnHtml}</div>
    `;
    return div;
}

// Search Logic
function setupSearch() {
    const input = document.getElementById('match-search');
    if(!input) return;
    input.addEventListener('keyup', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.match-row').forEach(row => {
            const match = row.dataset.search.includes(term);
            row.style.display = match ? 'grid' : 'none';
            // Logic to move match to top can go here, but simple hide/show is faster
        });
    });
}

// Footer Popup Logic
window.openSearchPopup = function(keyword) {
    const p = document.getElementById('keywordPopup');
    document.getElementById('kp-term').textContent = keyword;
    p.style.display = 'flex';
    setTimeout(() => {
        window.location.href = '/'; // Reload to home
    }, 2500);
};

// Player Logic
window.openPlayer = function(id, encoded, title) {
    const m = document.getElementById('vModal');
    const c = document.getElementById('vContainer');
    try {
        const url = atob(encoded);
        c.innerHTML = `<iframe src="${url}" style="width:100%;height:100%;border:0;" allow="autoplay; fullscreen"></iframe>`;
        m.style.display = 'flex';
        history.pushState({p:true}, title, `?watch=${id}`);
    } catch(e) {}
};

window.closeStream = function() {
    document.getElementById('vModal').style.display = 'none';
    document.getElementById('vContainer').innerHTML = '';
    if(history.state && history.state.p) history.back();
};

function showAllTrending() {
    document.querySelectorAll('.hidden-trend').forEach(el => el.classList.remove('hidden-trend'));
    document.getElementById('btnShowMore').style.display = 'none';
}

function kFormatter(num) {
    return Math.abs(num) > 999 ? Math.sign(num)*((Math.abs(num)/1000).toFixed(1)) + 'k' : Math.sign(num)*Math.abs(num);
}

function getSportIcon(sport) {
    const icons = {"NBA":"🏀","NFL":"🏈","UFC":"🥊","MLB":"⚾","Soccer":"⚽","F1":"🏎️"};
    return icons[sport] || "🏆";
}
