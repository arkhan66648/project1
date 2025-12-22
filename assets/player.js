// assets/player.js
// Handles Crypto loading, Player Layout, and Stream Playback

const SECRET_KEY = "12345678901234567890123456789012"; 

// 1. HELPER: Load Crypto Library
async function ensureCrypto() {
    if (window.CryptoJS) return;
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.2.0/crypto-js.min.js";
        script.onload = resolve;
        script.onerror = () => reject(new Error("Failed to load Crypto Library"));
        document.head.appendChild(script);
    });
}

// 2. HELPER: Decrypt Logic
function decryptStreamUrl(encryptedString) {
    try {
        if (!window.CryptoJS) return null;
        const parts = encryptedString.split(':');
        if (parts.length !== 2) return null;

        const iv = CryptoJS.enc.Hex.parse(parts[0]);
        const ct = CryptoJS.enc.Hex.parse(parts[1]);
        const key = CryptoJS.enc.Utf8.parse(SECRET_KEY);
        
        const dec = CryptoJS.AES.decrypt(
            { ciphertext: ct }, 
            key, 
            { iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
        );
        return dec.toString(CryptoJS.enc.Utf8);
    } catch (e) {
        console.error("Decryption Error:", e);
        return null;
    }
}

// 3. MAIN INITIALIZER
window.initPlayer = async function(matchData, isLocked) {
    // Note: isLocked param is kept for compatibility but not used for blocking anymore 
    // because master_template handles the info overlay.
    
    window.currentMatchData = matchData;
    const modal = document.getElementById('streamModal');
    if(!modal) return;

    // A. INJECT CSS ONCE
    if(!document.getElementById('player-styles')) {
        const style = document.createElement('style');
        style.id = 'player-styles';
        style.textContent = `
            :root { --brand-primary: #D00000; --bg-sidebar: #0f0f0f; }
            .player-layout { display: grid; grid-template-columns: 1fr 350px; grid-template-rows: 55px 1fr; height: 100vh; width: 100%; background: #050505; color: #eee; overflow:hidden; }
            @media (max-width: 900px) {
                .player-layout { display: flex; flex-direction: column; height: 100%; overflow-y: auto; }
                .video-stage { flex: 0 0 auto; }
                .sidebar { flex: 1; min-height: 400px; }
            }
            .overlay-header { grid-column: 1 / -1; background: #080808; border-bottom: 1px solid #222; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 50; }
            .back-nav { display: flex; align-items: center; gap: 8px; color: #999; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; cursor: pointer; }
            .back-nav:hover { color: white; }
            .back-nav svg { width: 18px; fill: currentColor; }
            
            .video-stage { grid-column: 1 / 2; display: flex; flex-direction: column; background: black; position: relative; overflow-y: auto; }
            .video-wrapper { position: relative; width: 100%; padding-top: 56.25%; background: #000; z-index: 10; }
            .video-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
            .video-msg { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #888; font-size: 0.9rem; gap: 10px; }
            
            .controls-container { padding: 20px; }
            .links-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; }
            .srv-btn { background: #111; border: 1px solid #333; color: #888; padding: 8px 16px; border-radius: 4px; font-size: 0.8rem; font-weight: 700; cursor: pointer; transition: 0.2s; }
            .srv-btn:hover { background: #222; color: #fff; }
            .srv-btn.active { background: var(--brand-primary); border-color: var(--brand-primary); color: white; }
            .more-btn { border-style: dashed; }
            .hidden-links-box { display: none; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; background: #0e0e0e; padding: 10px; margin-bottom: 15px; border:1px solid #222; border-radius:4px; }
            .hidden-links-box.show { display: grid; }

            .sidebar { grid-column: 2 / 3; background: var(--bg-sidebar); border-left: 1px solid #222; display: flex; flex-direction: column; }
            .chat-container { flex: 1; display: flex; flex-direction: column; min-height: 0; }
            .chat-messages { flex: 1; overflow-y: auto; padding: 10px; }
            .c-msg { padding: 4px 0; font-size: 0.85rem; color: #ccc; border-bottom: 1px solid #1a1a1a; }
            .u-name { font-weight: 700; color: #777; margin-right: 5px; }
            .chat-footer { padding: 10px; border-top: 1px solid #222; background: #080808; }
            .chat-input { width: 100%; background: #111; border: 1px solid #333; padding: 8px; color: white; border-radius: 4px; }
            .pulse-dot { width: 8px; height: 8px; background: #444; border-radius: 50%; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        `;
        document.head.appendChild(style);
    }

    const m = matchData;
    const matchTitle = m.team_b ? `${m.team_a} vs ${m.team_b}` : m.team_a;
    const leagueTitle = m.tournament || m.league || m.sport;

    // B. BUILD LAYOUT
    modal.innerHTML = `
        <div class="player-layout">
            <header class="overlay-header">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div class="back-nav" onclick="closeStreamModal()">
                        <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
                        <span>Back</span>
                    </div>
                    <div style="border-left:1px solid #333; padding-left:15px;">
                        <span style="font-size:0.75rem; color:#666; font-weight:800; text-transform:uppercase;">${leagueTitle}</span>
                        <div style="font-weight:700; font-size:0.95rem; color:white;">${matchTitle}</div>
                    </div>
                </div>
                <div><span style="font-size:0.8rem; font-weight:700; color:#444;">STREAMING</span></div>
            </header>

            <section class="video-stage">
                <div class="video-wrapper" id="videoWrapper">
                    <div class="video-msg">
                        <div class="pulse-dot"></div>
                        <span>Initializing Player...</span>
                    </div>
                </div>
                <div class="controls-container">
                    <div class="links-row" id="linksRow"></div>
                    <div class="hidden-links-box" id="hiddenLinksBox"></div>
                    <div style="font-size:0.75rem; color:#555; line-height:1.4;">
                        <strong>Note:</strong> If the stream does not load, please try a different server from the buttons above.
                    </div>
                </div>
            </section>

            <aside class="sidebar">
                <div class="chat-container">
                    <div style="padding:10px; border-bottom:1px solid #222; font-weight:700; font-size:0.8rem; color:#888;">LIVE CHAT</div>
                    <div class="chat-messages" id="chatFeed">
                        <div class="c-msg"><span class="u-name">System:</span> Welcome to the stream!</div>
                    </div>
                    <div class="chat-footer">
                        <input type="text" class="chat-input" id="chatIn" placeholder="Type message..." onkeypress="if(event.key==='Enter') sendChat()">
                    </div>
                </div>
            </aside>
        </div>
    `;

    modal.style.display = 'flex';
    
    // C. UPDATE URL
    if(history.pushState) {
        history.pushState({}, "", `/watch/${m.id}`);
    }

    // D. LOAD STREAMS & PLAY
    const vw = document.getElementById('videoWrapper');
    
    // Check if streams exist
    if (m.streams && m.streams.length > 0) {
        vw.innerHTML = '<div class="video-msg"><div class="pulse-dot"></div><span>Loading Decryption Library...</span></div>';
        
        try {
            await ensureCrypto(); // Load CryptoJS
            
            // Render Buttons
            renderStreamButtons(m.streams);

            // Auto Play First Stream
            playStream(m.streams[0], document.querySelector('.srv-btn')); // Pass first button

        } catch (e) {
            console.error(e);
            vw.innerHTML = '<div class="video-msg" style="color:red;">Failed to load security libraries.</div>';
        }
    } else {
        vw.innerHTML = '<div class="video-msg">No streams available for this match.</div>';
    }
};

// 4. HELPER: Render Buttons
function renderStreamButtons(streams) {
    const row = document.getElementById('linksRow');
    const hiddenBox = document.getElementById('hiddenLinksBox');
    row.innerHTML = ''; 
    hiddenBox.innerHTML = '';

    const createBtn = (s, i) => {
        const btn = document.createElement('button');
        btn.className = 'srv-btn';
        btn.innerText = s.source_name || `Server ${i+1}`;
        btn.onclick = () => playStream(s, btn);
        return btn;
    };

    // First 4 visible
    streams.slice(0, 4).forEach((s, i) => row.appendChild(createBtn(s, i)));

    // Rest hidden
    if (streams.length > 4) {
        const moreBtn = document.createElement('button');
        moreBtn.className = 'srv-btn more-btn';
        moreBtn.innerHTML = `+ ${streams.length - 4} More`;
        moreBtn.onclick = () => {
            hiddenBox.classList.toggle('show');
            moreBtn.innerHTML = hiddenBox.classList.contains('show') ? '- Close' : `+ ${streams.length - 4} More`;
        };
        row.appendChild(moreBtn);

        streams.slice(4).forEach((s, i) => hiddenBox.appendChild(createBtn(s, i + 4)));
    }
}

// 5. HELPER: Play Logic
function playStream(stream, btnElement) {
    // UI Update
    if (btnElement) {
        document.querySelectorAll('.srv-btn').forEach(b => b.classList.remove('active'));
        btnElement.classList.add('active');
    }

    const vw = document.getElementById('videoWrapper');
    vw.innerHTML = '<div class="video-msg"><div class="pulse-dot"></div><span>Connecting to Stream...</span></div>';

    // Get URL (Decrypt if needed)
    let finalUrl = stream.url;
    if (!finalUrl && stream.encrypted_data) {
        finalUrl = decryptStreamUrl(stream.encrypted_data);
    }

    if (finalUrl) {
        // Create Iframe
        const iframe = document.createElement('iframe');
        iframe.src = finalUrl;
        iframe.setAttribute('allow', 'autoplay; fullscreen; encrypted-media; picture-in-picture');
        iframe.setAttribute('scrolling', 'no');
        iframe.style.position = 'absolute';
        iframe.style.top = '0';
        iframe.style.left = '0';
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.backgroundColor = '#000'; // Prevent white flash
        
        vw.innerHTML = ''; // Clear loading message
        vw.appendChild(iframe);
    } else {
        vw.innerHTML = '<div class="video-msg" style="color:#ef4444;">Stream Link Error</div>';
    }
}

// 6. UTILS
window.sendChat = function() {
    const inp = document.getElementById('chatIn');
    if(!inp.value.trim()) return;
    const feed = document.getElementById('chatFeed');
    const d = document.createElement('div');
    d.className = 'c-msg';
    d.innerHTML = `<span class="u-name" style="color:${['#d32f2f','#7b1fa2','#1976d2','#388e3c'][Math.floor(Math.random()*4)]}">Guest:</span> ${inp.value}`;
    feed.appendChild(d);
    feed.scrollTop = feed.scrollHeight;
    inp.value = '';
}

window.closeStreamModal = function() {
    const m = document.getElementById('streamModal');
    m.style.display = 'none';
    m.innerHTML = ''; // Destroy iframe to stop audio
    history.pushState({}, "", "/");
}
