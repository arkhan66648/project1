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

// MAIN INITIALIZER
// isLocked = true (Direct Link): Show Info Overlay only. No Crypto/Iframe.
// isLocked = false (Watch Click): Load Player, Iframe, Chat.
window.initPlayer = async function(matchData, isLocked) {
    window.currentMatchData = matchData;
    const modal = document.getElementById('streamModal');
    
    // Inject Complex Player CSS
    if(!document.getElementById('player-styles')) {
        const style = document.createElement('style');
        style.id = 'player-styles';
        style.textContent = `
            :root { --brand-primary: #D00000; --status-live: #ff0000; --bg-sidebar: #0f0f0f; --bg-chat-hover: rgba(255,255,255,0.05); }
            .player-layout { display: grid; grid-template-columns: 1fr 350px; grid-template-rows: 55px 1fr; height: 100vh; width: 100%; background: #050505; color: #eee; }
            .overlay-header { grid-column: 1 / -1; background: #080808; border-bottom: 1px solid #222; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 50; }
            .header-left { display: flex; align-items: center; gap: 15px; }
            .back-nav { display: flex; align-items: center; gap: 8px; color: #999; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; cursor: pointer; }
            .back-nav:hover { color: white; }
            .back-nav svg { width: 18px; fill: currentColor; }
            .title-group { display: flex; align-items: center; gap: 10px; border-left: 1px solid #333; padding-left: 15px; margin-left: 5px; }
            .p-league-tag { font-size: 0.75rem; font-weight: 800; color: #555; letter-spacing: 1px; }
            .p-match-title { font-size: 1rem; font-weight: 700; color: white; letter-spacing: 0.5px; }
            .header-right { display: flex; align-items: center; gap: 15px; }
            .live-indicator { display: flex; align-items: center; gap: 6px; background: rgba(255,0,0,0.1); border: 1px solid rgba(255,0,0,0.3); color: var(--status-live); padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; }
            .pulse-dot { width: 6px; height: 6px; background: var(--status-live); border-radius: 50%; box-shadow: 0 0 8px var(--status-live); animation: pulse 1.5s infinite; }
            
            .video-stage { grid-column: 1 / 2; display: flex; flex-direction: column; background: black; overflow-y: auto; position: relative; }
            .video-wrapper { position: relative; width: 100%; padding-top: 56.25%; background: #000; box-shadow: 0 10px 40px rgba(0,0,0,0.5); z-index: 10; }
            .video-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
            
            /* Controls & Widgets */
            .controls-container { padding: 25px; max-width: 900px; margin: 0 auto; width: 100%; }
            .links-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 15px; }
            .srv-btn { background: #111; border: 1px solid #333; color: #888; padding: 8px 16px; border-radius: 4px; font-size: 0.8rem; font-weight: 700; transition: 0.2s; display: flex; align-items: center; gap: 6px; }
            .srv-btn:hover { border-color: #555; color: white; background: #1a1a1a; }
            .srv-btn.active { background: var(--brand-primary); border-color: var(--brand-primary); color: white; }
            .more-btn { background: transparent; border: 1px dashed #444; color: var(--brand-primary); }
            .hidden-links-box { display: none; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; background: #0e0e0e; padding: 15px; border-radius: 6px; border: 1px solid #222; margin-bottom: 15px; }
            .hidden-links-box.show { display: grid; }
            .disclaimer-text { font-size: 0.75rem; color: #555; line-height: 1.5; margin-bottom: 30px; border-left: 2px solid #333; padding-left: 10px; }
            
            /* Discord */
            .discord-card { background: linear-gradient(135deg, #5865F2 0%, #4752c4 100%); border-radius: 8px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; text-decoration: none; border: 1px solid rgba(255,255,255,0.1); color:white; }
            .dc-left { display: flex; align-items: center; gap: 15px; }
            .dc-logo { width: 44px; height: 44px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
            .dc-logo svg { width: 26px; height: 26px; fill: #5865F2; }
            .dc-text h4 { margin: 0; font-size: 1.05rem; font-weight: 800; }
            .dc-text p { margin: 3px 0 0 0; font-size: 0.8rem; opacity: 0.9; }
            .dc-btn { background: rgba(0,0,0,0.2); padding: 8px 16px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; border: 1px solid rgba(255,255,255,0.2); }
            
            /* Sidebar */
            .sidebar { grid-column: 2 / 3; background: var(--bg-sidebar); border-left: 1px solid #222; display: flex; flex-direction: column; height: 100%; z-index: 40; }
            .ad-slot-desktop { background: #000; border-bottom: 1px solid #222; display: flex; justify-content: center; align-items: center; padding:10px; }
            .ad-placeholder { width: 300px; height: 250px; background: #111; border: 1px dashed #333; display: flex; align-items: center; justify-content: center; color: #444; font-size: 0.7rem; position:relative; }
            .chat-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
            .chat-header { padding: 8px 15px; background: #111; border-bottom: 1px solid #222; font-size: 0.75rem; color: #999; font-weight: 700; text-transform: uppercase; }
            .chat-messages { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
            .c-msg { padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; color: #ddd; word-wrap: break-word; }
            .c-msg:hover { background: var(--bg-chat-hover); }
            .u-name { font-weight: 700; color: #aaa; margin-right: 5px; font-size: 0.8rem; }
            .chat-footer { padding: 10px; background: #0e0e0e; border-top: 1px solid #222; }
            .input-wrapper { display: flex; align-items: center; background: #181818; border: 1px solid #333; border-radius: 4px; }
            .chat-input { width: 100%; background: transparent; border: none; color: white; padding: 10px; font-size: 0.85rem; outline: none; }
            .send-btn { color: var(--brand-primary); font-weight: 700; font-size: 0.75rem; padding: 0 10px; background: none; }
            
            .ad-slot-mobile { display: none; }

            /* Overlay for Locked State */
            .info-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.9); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; z-index: 100; padding: 20px; }
            .io-title { font-size: 1.5rem; font-weight: 800; color: white; margin-bottom: 10px; }
            .io-meta { color: #888; font-size: 0.9rem; margin-bottom: 25px; }
            .io-btn { background: #D00000; color: white; font-size: 1.1rem; font-weight: 800; padding: 15px 40px; border-radius: 6px; box-shadow: 0 0 20px rgba(208,0,0,0.4); text-transform: uppercase; }
            .io-btn:hover { background: #b00000; transform: scale(1.05); }

            @media (max-width: 900px) {
                .player-layout { display: block; overflow-y: auto; }
                .overlay-header { position: sticky; top: 0; }
                .back-text { display: none; }
                .sidebar { width: 100%; height: auto; border: none; }
                .ad-slot-desktop { display: none; }
                .ad-slot-mobile { display: flex; justify-content: center; background: #080808; border-top: 1px solid #222; border-bottom: 1px solid #222; padding: 10px; }
                .chat-container { height: 400px; }
            }
        `;
        document.head.appendChild(style);
    }

    const m = matchData;
    const matchTitle = m.team_b ? `${m.team_a} vs ${m.team_b}` : m.team_a;
    const leagueTitle = m.tournament || m.league || m.sport;
    
    // HTML STRUCTURE
    modal.innerHTML = `
        <div class="player-layout">
            <header class="overlay-header">
                <div class="header-left">
                    <div class="back-nav" onclick="closeStreamModal()">
                        <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
                        <span class="back-text">Back</span>
                    </div>
                    <div class="title-group">
                        <span class="p-league-tag">${leagueTitle}</span>
                        <span style="color:#444; font-size:0.8rem; margin:0 5px;">/</span>
                        <span class="p-match-title">${matchTitle}</span>
                    </div>
                </div>
                <div class="header-right">
                    <div class="live-indicator"><div class="pulse-dot"></div> ${m.is_live ? 'LIVE' : 'OFFLINE'}</div>
                </div>
            </header>

            <section class="video-stage">
                <div class="video-wrapper" id="videoWrapper">
                    <!-- CONTENT INJECTED HERE (Overlay or Iframe) -->
                </div>

                <div class="controls-container">
                    <div class="links-row" id="linksRow">
                        <!-- Server buttons injected here -->
                    </div>
                    
                    <div class="hidden-links-box" id="hiddenLinksBox">
                        <!-- More links -->
                    </div>

                    <div class="disclaimer-text">
                        <strong>Disclaimer:</strong> StreamEast acts as a search engine for streams embedded on other websites. We do not host any copyrighted content. If the stream is buffering, please select a different server from the list above.
                    </div>

                    <a href="#" class="discord-card">
                        <div class="dc-left">
                            <div class="dc-logo"><svg viewBox="0 0 24 24"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/></svg></div>
                            <div class="dc-text"><h4>StreamEast Community</h4><p>Join 45,000+ members</p></div>
                        </div>
                        <div class="dc-btn">Join Now</div>
                    </a>
                </div>
            </section>

            <div class="ad-slot-mobile">
                <div class="ad-placeholder"><span style="position:absolute;top:2px;right:4px;font-size:8px;">AD</span>Mobile 300x250</div>
            </div>

            <aside class="sidebar">
                <div class="ad-slot-desktop">
                    <div class="ad-placeholder"><span style="position:absolute;top:2px;right:4px;font-size:8px;">AD</span>Desktop 300x250</div>
                </div>
                <div class="chat-container">
                    <div class="chat-header"><span>Stream Chat</span> <span style="color:var(--status-live);">● 14.5k</span></div>
                    <div class="chat-messages" id="chatFeed">
                        <div class="c-msg"><span class="u-name" style="color:#D00000">Sys:</span> Welcome to official stream.</div>
                    </div>
                    <div class="chat-footer">
                        <div class="input-wrapper">
                             <input type="text" class="chat-input" id="chatIn" placeholder="Send a message...">
                             <button class="send-btn" onclick="sendChat()">SEND</button>
                        </div>
                    </div>
                </div>
            </aside>
        </div>
    `;

    modal.style.display = 'flex';

    const vw = document.getElementById('videoWrapper');
    
    // --- STATE HANDLER ---
    if(isLocked) {
        // LOCKED: Show Overlay with Info
        vw.innerHTML = `
            <div class="info-overlay">
                <div class="io-title">${matchTitle}</div>
                <div class="io-meta">${m.formatted_date} • ${m.status_text || 'Upcoming'}</div>
                <button class="io-btn" onclick="unlockPlayerLogic()">▶ WATCH NOW</button>
            </div>
        `;
    } else {
        // UNLOCKED: Load Iframe logic
        await unlockPlayerLogic();
    }
};

// UNLOCK LOGIC (Transitions from Overlay to Stream)
window.unlockPlayerLogic = async function() {
    // 1. Update URL
    const m = window.currentMatchData;
    history.pushState({}, "", `/watch/${m.id}`);

    // 2. Prep UI
    const vw = document.getElementById('videoWrapper');
    vw.innerHTML = '<div style="color:#888; position:absolute; inset:0; display:flex; justify-content:center; align-items:center;">Loading secure stream...</div>';

    // 3. Render Server Buttons
    const row = document.getElementById('linksRow');
    const hiddenBox = document.getElementById('hiddenLinksBox');
    row.innerHTML = ''; hiddenBox.innerHTML = '';
    
    if(m.streams && m.streams.length > 0) {
        // Show first 3 inline
        m.streams.slice(0, 3).forEach((s, i) => {
            const btn = document.createElement('button');
            btn.className = i===0 ? 'srv-btn active' : 'srv-btn';
            btn.innerHTML = `Server ${i+1}`;
            btn.onclick = () => playStream(s, btn);
            row.appendChild(btn);
        });

        // Show "More" button if needed
        if(m.streams.length > 3) {
            const moreBtn = document.createElement('button');
            moreBtn.className = 'srv-btn more-btn';
            moreBtn.innerHTML = '+ More Links';
            moreBtn.onclick = () => {
                hiddenBox.classList.toggle('show');
                moreBtn.innerHTML = hiddenBox.classList.contains('show') ? '- Less Links' : '+ More Links';
            };
            row.appendChild(moreBtn);

            // Populate hidden box
            m.streams.slice(3).forEach((s, i) => {
                const btn = document.createElement('button');
                btn.className = 'srv-btn';
                btn.innerHTML = `Ext ${i+1}`;
                btn.onclick = () => playStream(s, btn);
                hiddenBox.appendChild(btn);
            });
        }
        
        // 4. Decrypt & Play first stream
        await ensureCrypto();
        playStream(m.streams[0], row.children[0]);

    } else {
        vw.innerHTML = '<div style="color:#aaa; display:flex; justify-content:center; align-items:center; height:100%;">No streams available.</div>';
    }
};

// PLAY STREAM
function playStream(stream, btnElement) {
    if(btnElement) {
        document.querySelectorAll('.srv-btn').forEach(b => {
            if(!b.classList.contains('more-btn')) b.classList.remove('active');
        });
        btnElement.classList.add('active');
    }

    const vw = document.getElementById('videoWrapper');
    vw.innerHTML = '<div style="color:#888; position:absolute; inset:0; display:flex; justify-content:center; align-items:center;">Decrypting source...</div>';

    let url = stream.url;
    if(stream.encrypted_data && !url) {
        try {
            const parts = stream.encrypted_data.split(':');
            const iv = CryptoJS.enc.Hex.parse(parts[0]);
            const ct = CryptoJS.enc.Hex.parse(parts[1]);
            const key = CryptoJS.enc.Utf8.parse(SECRET_KEY);
            const dec = CryptoJS.AES.decrypt({ciphertext: ct}, key, {iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7});
            url = dec.toString(CryptoJS.enc.Utf8);
        } catch(e) { console.error(e); }
    }

    if(url) {
        vw.innerHTML = `<iframe src="${url}" allow="autoplay; fullscreen; encrypted-media" scrolling="no"></iframe>`;
    } else {
        vw.innerHTML = '<div style="color:red; display:flex; justify-content:center; align-items:center; height:100%;">Stream Load Error</div>';
    }
}

// CHAT
window.sendChat = function() {
    const inp = document.getElementById('chatIn');
    if(!inp.value.trim()) return;
    const feed = document.getElementById('chatFeed');
    const d = document.createElement('div');
    d.className = 'c-msg';
    d.innerHTML = `<span class="u-name" style="color:#aaa">Guest:</span> ${inp.value}`;
    feed.appendChild(d);
    feed.scrollTop = feed.scrollHeight;
    inp.value = '';
}

// CLOSE MODAL
window.closeStreamModal = function() {
    const m = document.getElementById('streamModal');
    m.style.display = 'none';
    m.innerHTML = ''; // Destroy iframe
    history.pushState({}, "", "/");
}
