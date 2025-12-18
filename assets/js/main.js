// Global State
let allMatches = [];
let countdownInterval;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    initLazyAnalytics();
});

async function initApp() {
    // 1. Check for Internal Search (Footer Keywords)
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    if (q) triggerSearchPopup(q);

    // 2. Load Data
    await loadMatches();

    // 3. Start Global Countdown Timer
    startCountdowns();
    
    // 4. Setup Search Listener
    const searchInput = document.getElementById('match-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => handleSearch(e.target.value));
    }
}

// ==============================================
// 1. DATA LOADING & RENDERING
// ==============================================
async function loadMatches() {
    try {
        const res = await fetch('data/matches.json?t=' + Date.now());
        const data = await res.json();
        allMatches = data;

        // Container Elements
        const liveContainer = document.getElementById('live-matches-container');
        const upcomingWrapper = document.getElementById('upcoming-wrapper');
        const onlineCountEl = document.getElementById('onlineCount');

        // Reset
        if (liveContainer) liveContainer.innerHTML = '';
        if (upcomingWrapper) upcomingWrapper.innerHTML = '';

        // --- A. RENDER TRENDING (Top Priority) ---
        const trending = data.important;
        
        // Update "6 Matches Online" text
        if (onlineCountEl) {
            const liveCount = trending.filter(m => m.is_live).length;
            onlineCountEl.innerText = `● ${liveCount} Matches Online`;
            onlineCountEl.style.color = liveCount > 0 ? 'var(--brand-primary)' : '#888';
        }

        if (liveContainer) {
            if (trending.length === 0) {
                liveContainer.innerHTML = `<div style="padding:20px;text-align:center;color:#666">No trending matches right now.</div>`;
            } else {
                trending.forEach((match, index) => {
                    const row = createMatchRow(match, true); // true = isTrending
                    // Initial Limit: Show 5, Hide rest
                    if (index >= 5) row.classList.add('hidden-trend');
                    liveContainer.appendChild(row);
                });

                // Show More Button Logic
                const btnMore = document.getElementById('btnShowMore');
                if (trending.length > 5 && btnMore) {
                    btnMore.style.display = 'inline-block';
                    btnMore.textContent = `Show ${trending.length - 5} More Matches ▼`;
                    btnMore.onclick = () => {
                        document.querySelectorAll('.hidden-trend').forEach(el => el.classList.remove('hidden-trend'));
                        btnMore.style.display = 'none';
                    };
                }
            }
        }

        // --- B. RENDER UPCOMING (Categorized) ---
        if (upcomingWrapper) {
            // Sort categories by Priority (defined in Backend, but enforced here too)
            const priority = ["NFL", "NBA", "UFC", "MLB", "NHL", "Soccer", "F1", "Boxing"];
            const cats = Object.keys(data.categories).sort((a, b) => {
                let idxA = priority.indexOf(a); let idxB = priority.indexOf(b);
                if (idxA === -1) idxA = 99; if (idxB === -1) idxB = 99;
                return idxA - idxB;
            });

            cats.forEach(sport => {
                const matches = data.categories[sport].filter(m => !m.is_live); // Only upcoming
                if (matches.length > 0) {
                    // Create Section Wrapper
                    const section = document.createElement('div');
                    section.className = 'sport-section';
                    section.dataset.sport = sport.toLowerCase();
                    
                    // Header
                    section.innerHTML = `
                        <div class="sec-head">
                            <div class="sec-title">${getSportIcon(sport)} ${sport} Schedule</div>
                            <a href="/${sport.toLowerCase()}/" class="sec-right-link">View more ></a>
                        </div>
                        <div class="match-list" id="list-${sport}"></div>
                    `;
                    upcomingWrapper.appendChild(section);

                    // Rows (Limit to 24h/Top 4 for Homepage, All for subpages)
                    const container = section.querySelector(`#list-${sport}`);
                    const limit = window.IS_SUBPAGE ? 50 : 4; 
                    
                    matches.slice(0, limit).forEach(m => {
                        container.appendChild(createMatchRow(m, false));
                    });
                }
            });
        }

        // --- C. DYNAMIC SCHEMA (Live Badge) ---
        // Inject JSON-LD if a match is live
        const liveEvent = trending.find(m => m.is_live);
        const schemaScript = document.getElementById('dynamic-schema');
        if (liveEvent && schemaScript) {
            const schema = {
                "@context": "https://schema.org",
                "@type": "BroadcastEvent",
                "isLiveBroadcast": true,
                "name": liveEvent.title,
                "startDate": new Date(liveEvent.start_time).toISOString(),
                "eventStatus": "https://schema.org/EventLive",
                "location": { "@type": "VirtualLocation", "url": window.location.href }
            };
            schemaScript.textContent = JSON.stringify(schema);
        }

    } catch (err) {
        console.error("Error loading matches:", err);
    }
}

// ==============================================
// 2. MATCH ROW GENERATOR (The UI)
// ==============================================
function createMatchRow(match, isTrending) {
    const div = document.createElement('div');
    // Class logic
    div.className = match.is_live ? 'match-row live' : 'match-row';
    // Search Data
    div.dataset.search = (match.title + " " + match.sport + " " + match.league).toLowerCase();

    // 1. TIME COLUMN
    let timeHtml = '';
    const date = new Date(match.start_time);
    
    if (match.is_live) {
        timeHtml = `<span class="live-txt">LIVE</span>`;
        // Calculating "Match Time" is hard without API support, so we show generic "Live"
        // or we could show start time: <span class="time-sub">${date.getHours()}:${date.getMinutes()}</span>
    } else {
        // Countdown ID logic
        const msUntil = match.start_time - Date.now();
        if (msUntil > 0 && msUntil < 86400000) { // Less than 24h
            timeHtml = `<span class="countdown" data-time="${match.start_time}">Loading...</span>`;
        } else {
            timeHtml = `<span class="time-main">${date.toLocaleDateString([], {month:'short', day:'numeric'})}</span>`;
        }
        timeHtml += `<span class="time-sub">${date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>`;
    }

    // 2. INFO COLUMN (Teams & League)
    // Teams UI comes from backend (Array of objects with name, letter, color)
    let teamHtml = '';
    const teams = match.teams_ui || [];
    
    if (teams.length > 0) {
        // Team 1
        teamHtml += `<div class="team-name">
            <span class="t-circle" style="background:${teams[0].color}">${teams[0].letter}</span>
            ${teams[0].name}
        </div>`;
        
        // Team 2 (Only if exists - F1/Golf logic)
        if (teams.length > 1) {
            teamHtml += `<div class="team-name">
                <span class="t-circle" style="background:${teams[1].color}">${teams[1].letter}</span>
                ${teams[1].name}
            </div>`;
        }
    } else {
        // Fallback if no parsed teams
        teamHtml = `<div class="team-name">${match.title}</div>`;
    }

    // Sub-Category (e.g., La Liga instead of Soccer)
    const leagueTag = `<div class="league-tag">${match.league || match.sport}</div>`;

    // 3. META COLUMN (Hype Visuals)
    let metaHtml = '';
    if (match.is_live) {
        const v = match.viewers; // Already multiplied by backend
        let icon = '⚡ Stable'; // Default < 1k
        if (v >= 10000) icon = `🔥 ${kFormatter(v)}`;
        else if (v >= 1000) icon = `📈 ${kFormatter(v)}`;
        
        metaHtml = `<div class="meta-top">${icon}</div><div class="meta-bot">HD</div>`;
    } else {
        metaHtml = `<div class="meta-top" style="color:#666">⏳</div><div class="meta-bot">HD</div>`;
    }

    // 4. ACTION COLUMN
    let btnHtml = '';
    if (match.show_button) {
        // Security: Get encoded ID from first stream
        const streamEnc = match.streams && match.streams[0] ? match.streams[0].id : '';
        const safeTitle = match.title.replace(/['"]/g, ""); // Escape quotes
        
        // No HREF. Pure JS onclick.
        btnHtml = `<button class="btn-watch" onclick="openPlayer('${match.id}', '${streamEnc}', '${safeTitle}')">WATCH</button>`;
    } else {
        // Notify Button
        btnHtml = `<button class="btn-watch btn-notify" onclick="toggleNotify(this)">🔔 Notify</button>`;
    }

    div.innerHTML = `
        <div class="col-time">${timeHtml}</div>
        <div class="col-info">${leagueTag}${teamHtml}</div>
        <div class="col-meta">${metaHtml}</div>
        <div class="col-action">${btnHtml}</div>
    `;

    return div;
}

// ==============================================
// 3. SMART SEARCH
// ==============================================
function handleSearch(term) {
    const cleanTerm = term.toLowerCase().trim();
    const clearBtn = document.getElementById('searchClear');
    
    // Toggle Clear Button
    if (clearBtn) clearBtn.style.display = cleanTerm ? 'flex' : 'none';

    // 1. Filter Rows
    const rows = document.querySelectorAll('.match-row');
    let hasResults = false;

    rows.forEach(row => {
        const text = row.dataset.search || "";
        const isMatch = text.includes(cleanTerm);
        row.classList.toggle('hidden', !isMatch);
        if (isMatch) hasResults = true;
    });

    // 2. Hide Empty Sections (The "Smart" Part)
    document.querySelectorAll('.sport-section').forEach(section => {
        const visibleRows = section.querySelectorAll('.match-row:not(.hidden)').length;
        section.style.display = visibleRows > 0 ? 'block' : 'none';
        
        // Priority: If searching "UFC", bring UFC section to top view?
        // Simple approach: CSS order or just rely on hiding others. 
        // Hiding others is cleaner.
    });

    // 3. Empty State
    // (Optional: Show "No results" div if !hasResults)
}

function clearSearch() {
    const input = document.getElementById('match-search');
    if (input) {
        input.value = '';
        handleSearch('');
        input.focus();
    }
}

// ==============================================
// 4. PLAYER & CLOAKING LOGIC
// ==============================================
function openPlayer(id, encodedLink, title) {
    const modal = document.getElementById('vModal');
    const container = document.getElementById('vContainer');
    const titleEl = document.getElementById('vmTitle'); // If exists in template

    if (!encodedLink) { alert("Stream not available yet."); return; }

    // 1. Decode (Base64)
    let url = "";
    try { url = atob(encodedLink); } catch(e) { console.error("Link Error"); return; }

    // 2. Embed
    container.innerHTML = `<iframe src="${url}" style="width:100%;height:100%;border:0;" allow="autoplay; fullscreen; encrypted-media"></iframe>`;
    if(titleEl) titleEl.innerText = title;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Stop scrolling

    // 3. Cloak URL (Push State)
    // Changes browser URL to /?watch=123 without reloading
    const newUrl = `?watch=${id}`;
    history.pushState({ isPlayer: true }, title, newUrl);
}

// Global Close Function (Window scope for onclicks)
window.closeStream = function() {
    const modal = document.getElementById('vModal');
    const container = document.getElementById('vContainer');
    
    modal.style.display = 'none';
    container.innerHTML = ''; // Kill Iframe to stop audio
    document.body.style.overflow = '';

    // Revert URL
    if (history.state && history.state.isPlayer) {
        history.back();
    }
}

// Handle Browser Back Button
window.addEventListener('popstate', (e) => {
    const modal = document.getElementById('vModal');
    if (modal.style.display === 'flex') {
        window.closeStream(); // This might double-call history.back but it's safe
    }
});

// ==============================================
// 5. FEATURES (Notify, Countdowns, Popups)
// ==============================================

// Notify Button Logic
window.toggleNotify = function(btn) {
    if (btn.innerText.includes("Notify")) {
        btn.innerHTML = "✅ Set";
        btn.classList.add('set');
        // Optional: Save to LocalStorage
    } else {
        btn.innerHTML = "🔔 Notify";
        btn.classList.remove('set');
    }
}

// Footer Search Popup (Entity Stacking)
window.handlePartnerTerm = function(keyword) {
    const popup = document.getElementById('keywordPopup');
    const termSpan = document.getElementById('kp-term');
    
    if (popup && termSpan) {
        termSpan.innerText = keyword;
        popup.style.display = 'flex';
        
        // Delay 2s then Redirect/Reload
        setTimeout(() => {
            window.location.href = '/'; 
        }, 2000);
    }
}

// Trigger popup from URL param (?q=methstreams)
function triggerSearchPopup(keyword) {
    const partnerKeywords = ["methstreams", "crackstreams", "buffstreams", "sportsurge", "streameast"];
    const clean = keyword.toLowerCase().trim();
    
    // Only trigger warning box on homepage, or popup logic
    if (partnerKeywords.some(k => clean.includes(k))) {
        // Show the inline warning box defined in HTML
        const box = document.getElementById('searchMsgBox');
        if (box) {
            box.style.display = 'block';
            const span = document.getElementById('searchTermDisplay');
            if (span) span.innerText = clean.toUpperCase();
            box.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

// Countdown Logic
function startCountdowns() {
    // Run once immediately
    updateTimers();
    // Run every minute
    countdownInterval = setInterval(updateTimers, 60000);
}

function updateTimers() {
    const elements = document.querySelectorAll('.countdown');
    const now = Date.now();

    elements.forEach(el => {
        const start = parseInt(el.dataset.time);
        const diff = start - now;

        if (diff <= 0) {
            // Match started!
            el.className = 'live-txt';
            el.innerText = "LIVE";
        } else {
            // Format time
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            
            if (hours > 24) {
                el.innerText = new Date(start).toLocaleDateString();
            } else {
                // "02h 15m" format
                el.innerText = `${String(hours).padStart(2,'0')}h ${String(mins).padStart(2,'0')}m`;
            }
        }
    });
}

// ==============================================
// 6. LAZY ANALYTICS (Performance)
// ==============================================
function initLazyAnalytics() {
    if (!window.GA_ID) return; // Defined in HTML by Python

    let loaded = false;
    
    function loadGA() {
        if (loaded) return;
        loaded = true;
        
        // Inject Script
        const script = document.createElement('script');
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${window.GA_ID}`;
        document.head.appendChild(script);

        // Init Data
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', window.GA_ID);
        
        console.log("GA Loaded");
    }

    // 1. Interaction Trigger
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    const onInteract = () => {
        events.forEach(e => window.removeEventListener(e, onInteract));
        setTimeout(loadGA, 2000); // 2s delay after interaction
    };
    events.forEach(e => window.addEventListener(e, onInteract));

    // 2. Fallback Trigger (4s)
    setTimeout(loadGA, 4000); 
}

// ==============================================
// 7. UTILS
// ==============================================
function kFormatter(num) {
    return Math.abs(num) > 999 ? Math.sign(num)*((Math.abs(num)/1000).toFixed(1)) + 'k' : Math.sign(num)*Math.abs(num);
}

function getSportIcon(sport) {
    const icons = {
        "NBA": "🏀", "NFL": "🏈", "UFC": "🥊", "MLB": "⚾", 
        "NHL": "🏒", "Soccer": "⚽", "F1": "🏎️", "Boxing": "🥊", "Tennis": "🎾"
    };
    return icons[sport] || "🏆";
}
