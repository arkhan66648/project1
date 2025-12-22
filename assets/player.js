// assets/player.js
// Handles lazy loading of Crypto, Player Layout, and Decryption
// Only runs when triggered by openPlayer()

const SECRET_KEY = "12345678901234567890123456789012"; 

async function ensureCrypto() {
    if (window.CryptoJS) return;
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.2.0/crypto-js.min.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Ensure the function is globally available
window.unlockPlayerLogic = async function() {
    const m = window.currentMatchData;
    
    // 1. Update URL to /watch/ID
    if(history.pushState) {
        history.pushState({}, "", `/watch/${m.id}`);
    }

    // 2. Prep UI Elements
    const vw = document.getElementById('videoWrapper');
    const row = document.getElementById('linksRow');
    const hiddenBox = document.getElementById('hiddenLinksBox');
    
    if(!vw || !row || !hiddenBox) return;

    // Set initial loading state
    vw.innerHTML = '<div style="color:#888; position:absolute; inset:0; display:flex; justify-content:center; align-items:center; flex-direction:column; gap:10px;"><div class="pulse-dot" style="background:#444;box-shadow:none;"></div><span>Loading secure stream...</span></div>';
    row.innerHTML = ''; 
    hiddenBox.innerHTML = '';
    
    // 3. Render Server Buttons
    if(m.streams && m.streams.length > 0) {
        // Prepare Crypto lib
        await ensureCrypto();

        const createBtn = (s, i, isMain) => {
            const btn = document.createElement('button');
            btn.className = 'srv-btn';
            // Use source_name if available, else Server 1, 2...
            btn.innerText = s.source_name || `Server ${i+1}`;
            btn.onclick = () => playStream(s, btn);
            return btn;
        };

        // Main Buttons (Show first 4 inline)
        m.streams.slice(0, 4).forEach((s, i) => {
            const btn = createBtn(s, i, true);
            row.appendChild(btn);
        });

        // Hidden Buttons (Show rest in dropdown)
        if(m.streams.length > 4) {
            const moreBtn = document.createElement('button');
            moreBtn.className = 'srv-btn more-btn';
            moreBtn.innerHTML = `+ ${m.streams.length - 4} More`;
            moreBtn.onclick = () => {
                hiddenBox.classList.toggle('show');
                moreBtn.innerHTML = hiddenBox.classList.contains('show') ? '- Close' : `+ ${m.streams.length - 4} More`;
            };
            row.appendChild(moreBtn);

            m.streams.slice(4).forEach((s, i) => {
                const btn = createBtn(s, i + 4, false);
                hiddenBox.appendChild(btn);
            });
        }
        
        // 4. Auto Play First Stream
        // Small delay to ensure UI is painted
        setTimeout(() => {
            if(row.children[0]) {
                playStream(m.streams[0], row.children[0]);
            }
        }, 100);

    } else {
        vw.innerHTML = '<div style="color:#aaa; position:absolute; inset:0; display:flex; justify-content:center; align-items:center;">No streams available.</div>';
    }
};

window.initPlayer = async function(matchData, isLocked) {
    // Note: isLocked is ignored here because master_template.html handles the locking overlay.
    // This function is only called when the user is allowed to watch.
    
    window.currentMatchData = matchData;
    const modal = document.getElementById('streamModal');
    if(!modal) return;
    
    // CSS INJECTION (Optimized & Cleaned)
    if(!document.getElementById('player-styles')) {
        const style = document.createElement('style');
        style.id = 'player-styles';
        style.textContent = `
            :root { --brand-primary: #D00000; --bg-sidebar: #0f0f0f; }
            
            .player-layout { display: grid; grid-template-columns: 1fr 350px; grid-template-rows: 55px 1fr; height: 100vh; width: 100%; background: #050505; color: #eee; overflow:hidden; }
            
            /* Mobile Responsiveness */
            @media (max-width: 900px) {
                .player-layout { display: flex; flex-direction: column; height: 100%; overflow-y: auto; }
                .video-stage { flex: 0 0 auto; }
                .sidebar { flex: 1; min-height: 400px; }
            }

            .overlay-header { grid-column: 1 / -1; background: #080808; border-bottom: 1px solid #222; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 50; }
            .header-left { display: flex; align-items: center; gap: 15px; }
            .back-nav { display: flex; align-items: center; gap: 8px; color: #999; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; cursor: pointer; }
            .back-nav:hover { color: white; }
            .back-nav svg { width: 18px; fill: currentColor; }
            
            .video-stage { grid-column: 1 / 2; display: flex; flex-direction: column; background: black; position: relative; overflow-y: auto; }
            
            /* Video Wrapper: 16:9 Aspect Ratio */
            .video-wrapper { position: relative; width: 100%; padding-top: 56.25%; background: #000; z-index: 10; }
            .video-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
            
            .controls-container { padding: 20px; }
            .links-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; }
            .srv-btn { background: #111; border: 1px solid #333; color: #888; padding: 6px 14px; border-radius: 4px; font-size: 0.8rem; font-weight: 700; cursor: pointer; transition: 0.2s; }
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
            
            .pulse-dot { width: 8px; height: 8px; background: red; border-radius: 50%; display:inline-block; animation: pulse 1s infinite; margin-right:5px; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        `;
        document.head.appendChild(style);
    }

    const m = matchData;
    const matchTitle = m.team_b ? `${m.team_a} vs ${m.team_b}` : m.team_a;
    const leagueTitle = m.tournament || m.league || m.sport;
    
    // Build Overlay HTML
    modal.innerHTML = `
        <div class="player-layout">
            <header class="overlay-header">
                <div class="header-left">
                    <div class="back-nav" onclick="closeStreamModal()">
                        <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
                        <span>Back</span>
                    </div>
                    <div style="margin-left:15px; border-left:1px solid #333; padding-left:15px;">
                        <span style="font-size:0.75rem; color:#666; font-weight:800; text-transform:uppercase;">${leagueTitle}</span>
                        <div style="font-weight:700; font-size:0.95rem; color:white;">${matchTitle}</div>
                    </div>
                </div>
                <div class="header-right">
                    <span style="font-size:0.8rem; font-weight:700; color:#444;">STREAMING</span>
                </div>
            </header>

            <section class="video-stage">
                <div class="video-wrapper" id="videoWrapper">
                    <!-- VIDEO LOADS HERE -->
                </div>
                <div class="controls-container">
                    <div class="links-row" id="linksRow">
                        <!-- BUTTONS LOAD HERE -->
                    </div>
                    <div class="hidden-links-box" id="hiddenLinksBox"></div>
                    <div style="font-size:0.75rem; color:#555; line-height:1.4;">
                        <strong>Disclaimer:</strong> This content is provided by 3rd party servers. We do not host any media.
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

    // Start Logic immediately (Skip "Locked" phase)
    await window.unlockPlayerLogic();
};

function playStream(stream, btnElement) {
    if(btnElement) {
        document.querySelectorAll('.srv-btn').forEach(b => b.classList.remove('active'));
        btnElement.classList.add('active');
    }

    const vw = document.getElementById('videoWrapper');
    
    // Show Loading Text inside wrapper
    vw.innerHTML = '<div style="color:#888; position:absolute; inset:0; display:flex; justify-content:center; align-items:center; flex-direction:column;"><div class="pulse-dot" style="background:#444;box-shadow:none;"></div><small>Connecting...</small></div>';

    let url = stream.url;
    
    // Decrypt if needed
    if(stream.encrypted_data && !url) {
        try {
            const parts = stream.encrypted_data.split(':');
            const iv = CryptoJS.enc.Hex.parse(parts[0]);
            const ct = CryptoJS.enc.Hex.parse(parts[1]);
            const key = CryptoJS.enc.Utf8.parse(SECRET_KEY);
            const dec = CryptoJS.AES.decrypt({ciphertext: ct}, key, {iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7});
            url = dec.toString(CryptoJS.enc.Utf8);
        } catch(e) { console.error("Decryption error", e); }
    }

    if(url) {
        // Standard Iframe Embed
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.setAttribute('allow', 'autoplay; fullscreen; encrypted-media; picture-in-picture');
        iframe.setAttribute('scrolling', 'no');
        iframe.style.position = 'absolute';
        iframe.style.top = '0';
        iframe.style.left = '0';
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        
        vw.innerHTML = ''; // Clear loading text
        vw.appendChild(iframe);
    } else {
        vw.innerHTML = '<div style="color:#ef4444; position:absolute; inset:0; display:flex; justify-content:center; align-items:center;">Stream Unavailable</div>';
    }
}

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
    m.innerHTML = ''; // Destroy content to stop audio
    history.pushState({}, "", "/");
}
