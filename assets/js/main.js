document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    // 1. Check for Partner Search Terms (Your trick)
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    if(q) handlePartnerTerm(q);

    // 2. Load Matches
    await loadMatches();
}

async function loadMatches() {
    try {
        const res = await fetch('data/matches.json?t=' + Date.now());
        const data = await res.json();
        
        const liveContainer = document.getElementById('live-matches-container');
        const upcomingContainer = document.getElementById('upcoming-matches-container');
        
        liveContainer.innerHTML = '';
        upcomingContainer.innerHTML = '';

        // 1. GENERATE DYNAMIC SCHEMA (Live Badge)
        const liveEvents = data.important.filter(m => m.is_live);
        if(liveEvents.length > 0) {
            const schemaData = {
                "@context": "https://schema.org",
                "@type": "BroadcastEvent",
                "isLiveBroadcast": true,
                "name": liveEvents[0].title, // Google usually picks the first one
                "startDate": new Date(liveEvents[0].start_time).toISOString(),
                "eventStatus": "https://schema.org/EventLive",
                "location": { "@type": "VirtualLocation", "url": window.location.href }
            };
            document.getElementById('dynamic-schema').textContent = JSON.stringify(schemaData);
        }

        // 2. RENDER LIVE MATCHES
        data.important.forEach(match => {
            const row = createRow(match);
            liveContainer.appendChild(row);
        });

        // 3. RENDER CATEGORY MATCHES (UPCOMING)
        // Just showing first 5 NFL/NBA for example
        let count = 0;
        const priority = ["NFL", "NBA", "UFC"];
        priority.forEach(sport => {
            if(data.categories[sport]) {
                data.categories[sport].slice(0, 2).forEach(m => {
                    if(!m.is_live) {
                         upcomingContainer.appendChild(createRow(m));
                    }
                });
            }
        });

    } catch (err) {
        console.error(err);
    }
}

function createRow(match) {
    const div = document.createElement('div');
    // Add 'live' class if match is live (for red border/gradient)
    div.className = match.is_live ? 'match-row live' : 'match-row';
    
    // Time Column
    const date = new Date(match.start_time);
    const timeStr = match.is_live 
        ? `<span class="live-txt">LIVE</span>` 
        : `<span class="time-main">${date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>`;

    // Teams Logic (Split title if possible, else show full)
    let teams = match.title.split(' vs ');
    if(teams.length < 2) teams = match.title.split(' - ');
    const team1 = teams[0] || match.title;
    const team2 = teams[1] || "";

    // Button Logic
    let btnHtml = `<button class="btn-watch btn-notify">🔔 Notify</button>`;
    if(match.show_button) {
        // Use the first stream ID
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
            <div class="team-name">${team1}</div>
            <div class="team-name">${team2}</div>
        </div>
        <div class="col-meta">
            <div class="meta-top">HD</div>
            <div class="meta-bot">${match.viewers ? '🔥 ' + kFormatter(match.viewers) : 'Wait'}</div>
        </div>
        <div class="col-action">
            ${btnHtml}
        </div>
    `;
    return div;
}

// Open Player (Uses your logic + Cloaking)
function openPlayer(id, encodedLink, title) {
    const modal = document.getElementById('vModal');
    const container = document.getElementById('vContainer');
    
    // 1. Decode Link
    let url = "";
    try { url = atob(encodedLink); } catch(e){ return; }

    // 2. Embed
    container.innerHTML = `<iframe src="${url}" style="width:100%;height:100%;border:0;" allow="autoplay; fullscreen"></iframe>`;
    modal.style.display = 'flex';

    // 3. Cloak URL
    history.pushState({player:true}, title, `?watch=${id}`);
}

function closeStream() {
    document.getElementById('vModal').style.display = 'none';
    document.getElementById('vContainer').innerHTML = '';
    if(history.state && history.state.player) history.back();
}

function handlePartnerTerm(term) {
    const partnerKeywords = ["methstreams", "crackstreams", "buffstreams", "sportsurge"];
    const cleanTerm = term.toLowerCase().trim();
    if (partnerKeywords.some(k => cleanTerm.includes(k))) {
        document.getElementById('searchMsgBox').style.display = 'block';
        document.getElementById('searchTermDisplay').innerText = cleanTerm.toUpperCase();
    }
}

function kFormatter(num) {
    return Math.abs(num) > 999 ? Math.sign(num)*((Math.abs(num)/1000).toFixed(1)) + 'k' : Math.sign(num)*Math.abs(num);
}

function toggleMenu() { document.getElementById('mobileMenu').classList.toggle('active'); }
