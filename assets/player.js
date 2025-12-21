// assets/player.js
// Handles lazy loading of Crypto, Player Layout, and Decryption
// Does NOT run on main page load, only when requested.

const SECRET_KEY = "12345678901234567890123456789012"; 

// 1. Lazy Load Crypto Library Function
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

// 2. Initialize Player
// isLocked = true: Came from Direct Link (/#id). Show Match Info Overlay ONLY.
// isLocked = false: Came from Watch Button. Show Player & Server List.
window.initPlayer = async function(matchData, isLocked) {
    window.currentMatchData = matchData;
    const modal = document.getElementById('streamModal');
    
    // Inject Styles for Player (Dynamically, so main page is clean)
    if(!document.getElementById('player-styles')) {
        const style = document.createElement('style');
        style.id = 'player-styles';
        style.textContent = `
            /* Professional Player Layout */
            .p-container { display: flex; flex-direction: column; height: 100%; width: 100%; background: #000; }
            .p-header { height: 50px; background: #111; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; padding: 0 15px; }
            .p-title { font-weight: 700; color: white; font-size: 0.9rem; }
            .p-close { background: #222; color: #fff; border: 1px solid #333; padding: 5px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; transition: 0.2s; }
            .p-close:hover { background: #D00000; border-color: #D00000; }
            
            .p-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
            
            /* The Video Area */
            .p-video { flex: 1; background: #000; position: relative; display: flex; align-items: center; justify-content: center; }
            
            /* Sidebar (Desktop) / Bottom (Mobile) */
            .p-sidebar { background: #0e0e0e; border-left: 1px solid #222; width: 300px; display: flex; flex-direction: column; overflow-y: auto; }
            .p-list-head { padding: 12px; color: #666; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; border-bottom: 1px solid #1a1a1a; }
            .p-server-btn { display: flex; align-items: center; justify-content: space-between; padding: 12px 15px; border-bottom: 1px solid #1a1a1a; background: #0e0e0e; color: #ccc; font-size: 0.85rem; width: 100%; text-align: left; transition:0.2s; }
            .p-server-btn:hover { background: #1a1a1a; color: white; }
            .p-server-btn.active { background: #1a1a1a; color: #D00000; border-left: 3px solid #D00000; }
            
            /* Info Overlay (Locked State) */
            .p-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.9); z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; }
            .p-overlay h2 { color: white; margin: 0 0 10px 0; font-size: 1.5rem; }
            .p-overlay p { color: #888; margin: 0 0 25px 0; }
            .p-overlay-close { position: absolute; top: 20px; right: 20px; font-size: 2rem; color: #666; cursor: pointer; }
            .p-overlay-close:hover { color: white; }
            
            .btn-big-watch { background: #D00000; color: white; font-size: 1rem; font-weight: 800; padding: 15px 40px; border-radius: 5px; text-transform: uppercase; box-shadow: 0 0 20px rgba(208,0,0,0.4); }
            .btn-big-watch:hover { transform: scale(1.05); background: #b00000; }

            @media (max-width: 900px) {
                .p-body { flex-direction: column; }
                .p-sidebar { width: 100%; height: 150px; border-left: none; border-top: 1px solid #222; }
            }
        `;
        document.head.appendChild(style);
    }

    // 3. Build Layout HTML
    const matchTitle = matchData.team_b 
        ? `${matchData.team_a} vs ${matchData.team_b}` 
        : matchData.team_a;

    // We build the layout string but we might obscure the video part if locked
    modal.innerHTML = `
        <div class="p-container">
            <div class="p-header">
                <div class="p-title">StreamEast Live</div>
                <button class="p-close" onclick="closeStreamModal()">Close Stream ✕</button>
            </div>
            <div class="p-body">
                <div class="p-video" id="videoContainer">
                    <!-- If Locked: Overlay is here. If Unlocked: Iframe is here. -->
                </div>
                <div class="p-sidebar" id="sidebarContainer" style="${isLocked ? 'display:none' : 'display:flex'}">
                    <div class="p-list-head">Select Server</div>
                    <div id="serverList"></div>
                </div>
            </div>
        </div>
    `;

    modal.style.display = 'flex';

    if (isLocked) {
        // --- LOCKED STATE: Show Info Overlay Only ---
        document.getElementById('videoContainer').innerHTML = `
            <div class="p-overlay">
                <div class="p-overlay-close" onclick="closeStreamModal()">&times;</div>
                <p style="text-transform:uppercase; color:#D00000; font-weight:700; letter-spacing:1px;">Match Preview</p>
                <h2>${matchTitle}</h2>
                <p>Status: ${matchData.is_live ? 'Live Now' : matchData.status_text}</p>
                <button class="btn-big-watch" onclick="unlockPlayer()">▶ WATCH LIVE</button>
            </div>
        `;
    } else {
        // --- UNLOCKED STATE: Load Stream Immediately ---
        await unlockPlayerLogic();
    }
};

// 4. Handle Unlocking (Clicking Watch)
window.unlockPlayer = async function() {
    // UI Update
    const overlay = document.querySelector('.p-overlay');
    if(overlay) overlay.innerHTML = '<div style="color:white;">Loading Stream...</div>';
    
    await unlockPlayerLogic();
};

async function unlockPlayerLogic() {
    const m = window.currentMatchData;
    
    // Update URL to /watch/id
    history.pushState({}, "", `/watch/${m.id}`);

    // Show Sidebar
    const sb = document.getElementById('sidebarContainer');
    if(sb) sb.style.display = 'flex';

    // Populate Sidebar
    const list = document.getElementById('serverList');
    list.innerHTML = '';
    
    if(!m.streams || m.streams.length === 0) {
        list.innerHTML = '<div style="padding:15px; color:#444;">No streams found.</div>';
        document.getElementById('videoContainer').innerHTML = '<div style="color:#666;">Stream Offline</div>';
        return;
    }

    m.streams.forEach((s, idx) => {
        const btn = document.createElement('button');
        btn.className = 'p-server-btn';
        if(idx === 0) btn.classList.add('active'); // Default active
        btn.innerHTML = `<span>Server ${idx+1}</span> <span style="font-size:0.7rem; background:#333; padding:2px 5px; border-radius:3px;">${s.source_name||'HD'}</span>`;
        btn.onclick = () => {
            document.querySelectorAll('.p-server-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            playStream(s);
        };
        list.appendChild(btn);
    });

    // Ensure Crypto & Play First Stream
    await ensureCrypto();
    playStream(m.streams[0]);
}

// 5. Decrypt and Play
function playStream(stream) {
    const container = document.getElementById('videoContainer');
    container.innerHTML = '<div style="color:#666;">Decrypting...</div>';

    let url = stream.url;

    if(stream.encrypted_data && !url) {
        try {
            const parts = stream.encrypted_data.split(':');
            if(parts.length === 2) {
                const iv = CryptoJS.enc.Hex.parse(parts[0]);
                const ciphertext = CryptoJS.enc.Hex.parse(parts[1]);
                const key = CryptoJS.enc.Utf8.parse(SECRET_KEY);
                const decrypted = CryptoJS.AES.decrypt(
                    { ciphertext: ciphertext },
                    key,
                    { iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
                );
                url = decrypted.toString(CryptoJS.enc.Utf8);
            }
        } catch(e) { console.error("Decryption Error", e); }
    }

    if(!url) {
        container.innerHTML = '<div style="color:red;">Error loading stream.</div>';
        return;
    }

    // Embed Iframe
    container.innerHTML = `<iframe src="${url}" style="width:100%; height:100%; border:none;" allow="autoplay; fullscreen; encrypted-media" scrolling="no"></iframe>`;
}

// 6. Close Modal
window.closeStreamModal = function() {
    document.getElementById('streamModal').style.display = 'none';
    document.getElementById('streamModal').innerHTML = ''; // Destroy Iframe to stop audio
    history.pushState({}, "", "/"); // Revert URL
};
