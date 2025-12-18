document.addEventListener("DOMContentLoaded", () => {
    loadMatches();
});

async function loadMatches() {
    try {
        const res = await fetch('data/matches.json?t=' + Date.now());
        const data = await res.json();
        
        const liveContainer = document.getElementById('live-matches-container');
        const upcomingContainer = document.getElementById('upcoming-matches-container');
        
        if(liveContainer) liveContainer.innerHTML = '';
        if(upcomingContainer) upcomingContainer.innerHTML = '';

        // 1. INJECT LIVE MATCHES
        data.important.forEach(match => {
            const row = createGridRow(match);
            if(liveContainer) liveContainer.appendChild(row);
        });

        // 2. INJECT UPCOMING (Group by Category for simple view)
        // Taking first 5 from each category as example
        const sports = ["NFL", "NBA", "UFC"];
        sports.forEach(sport => {
            if(data.categories[sport]) {
                data.categories[sport].slice(0, 3).forEach(m => {
                    if(!m.is_live && upcomingContainer) {
                        upcomingContainer.appendChild(createGridRow(m));
                    }
                });
            }
        });

        // 3. SCHEMA INJECTION (Live Badge)
        const liveEvent = data.important.find(m => m.is_live);
        if(liveEvent) {
            const schema = {
                "@context": "https://schema.org",
                "@type": "BroadcastEvent",
                "isLiveBroadcast": true,
                "name": liveEvent.title,
                "startDate": new Date(liveEvent.start_time).toISOString(),
                "eventStatus": "https://schema.org/EventLive",
                "location": { "@type": "VirtualLocation", "url": window.location.href }
            };
            document.getElementById('dynamic-schema').textContent = JSON.stringify(schema);
        }

    } catch (err) { console.error(err); }
}

function createGridRow(match) {
    const div = document.createElement('div');
    // Apply classes for your specific design
    div.className = match.is_live ? 'match-row live' : 'match-row';

    // Time Formatting
    const date = new Date(match.start_time);
    const timeStr = match.is_live 
        ? `<span class="live-txt">LIVE</span>` 
        : `<span class="time-main">${date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>`;
    
    // Team Splitter
    let parts = match.title.split(' vs ');
    if(parts.length < 2) parts = match.title.split(' - ');
    const t1 = parts[0] || match.title;
    const t2 = parts[1] || "";

    // Button Logic (Cloaking)
    let btnHtml = `<button class="btn-watch btn-notify">🔔 Notify</button>`;
    if(match.show_button) {
        const streamId = match.streams[0]?.id || "";
        const safeTitle = match.title.replace(/'/g, "");
        btnHtml = `<button class="btn-watch" onclick="openPlayer('${match.id}', '${streamId}', '${safeTitle}')">WATCH</button>`;
    }

    div.innerHTML = `
        <div class="col-time">
            ${timeStr}
            <span class="time-sub">${date.toLocaleDateString([], {month:'short', day:'numeric'})}</span>
        </div>
        <div class="col-info">
            <div class="league-tag">${match.sport}</div>
            <div class="team-name">${t1}</div>
            <div class="team-name">${t2}</div>
        </div>
        <div class="col-meta">
            <div class="meta-top">HD</div>
            <div class="meta-bot">${match.viewers ? kFormatter(match.viewers) : 'Wait'}</div>
        </div>
        <div class="col-action">
            ${btnHtml}
        </div>
    `;
    return div;
}

// Player Logic
function openPlayer(id, encoded, title) {
    const modal = document.getElementById('vModal');
    const container = document.getElementById('vContainer');
    
    let url = "";
    try { url = atob(encoded); } catch(e){ return; }

    container.innerHTML = `<iframe src="${url}" style="width:100%;height:100%;border:0;" allow="autoplay; fullscreen"></iframe>`;
    modal.style.display = 'flex';
    history.pushState({p:true}, title, `?watch=${id}`);
}

function closeStream() {
    document.getElementById('vModal').style.display = 'none';
    document.getElementById('vContainer').innerHTML = '';
    if(history.state && history.state.p) history.back();
}

function kFormatter(num) {
    return Math.abs(num) > 999 ? Math.sign(num)*((Math.abs(num)/1000).toFixed(1)) + 'k' : Math.sign(num)*Math.abs(num);
}
