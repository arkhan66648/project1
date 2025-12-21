// assets/player.js

const SECRET_KEY = "12345678901234567890123456789012"; // Match your backend key

window.initPlayer = function(matchData, isLocked) {
    window.currentMatchData = matchData; // Store for unlock usage

    const modal = document.getElementById('streamModal');
    const title = document.getElementById('playerTitle');
    const list = document.getElementById('streamList');
    const seoOverlay = document.getElementById('seoOverlay');
    const iframeBox = document.getElementById('iframeBox');

    // 1. Reset State
    list.innerHTML = '';
    const oldIframe = iframeBox.querySelector('iframe');
    if(oldIframe) oldIframe.remove();
    modal.style.display = 'flex';

    // 2. Set Title
    title.innerHTML = matchData.team_b 
        ? `${matchData.team_a} <span style="color:#888; font-size:0.8em;">VS</span> ${matchData.team_b}` 
        : matchData.team_a;

    // 3. Populate Server List
    if(!matchData.streams || matchData.streams.length === 0) {
        list.innerHTML = '<div style="padding:15px; color:#666; font-size:0.8rem;">No streams available at the moment.</div>';
    } else {
        matchData.streams.forEach((s, idx) => {
            const btn = document.createElement('button');
            btn.className = 'stream-btn';
            // Highlight first one if not locked
            if(idx === 0 && !isLocked) btn.classList.add('active');
            
            btn.innerHTML = `
                <span style="color:#888;">Server ${idx + 1}</span> 
                <span class="sig-hd">${s.source_name || 'HD'}</span>
            `;
            
            btn.onclick = () => loadIframeStream(s, btn);
            list.appendChild(btn);
        });
    }

    // 4. Handle Lock/Unlock Logic
    if(isLocked) {
        seoOverlay.style.display = 'flex';
        document.getElementById('seoVsText').innerText = matchData.team_b ? `${matchData.team_a} vs ${matchData.team_b}` : matchData.team_a;
        document.getElementById('seoTimeText').innerText = matchData.is_live ? "LIVE NOW" : matchData.status_text;
    } else {
        seoOverlay.style.display = 'none';
        // Auto-play first stream
        if(matchData.streams.length > 0) {
            loadIframeStream(matchData.streams[0], list.children[0]);
        }
        history.pushState({}, "", `/watch/${matchData.id}`);
    }
};

function loadIframeStream(stream, btnElement) {
    document.querySelectorAll('.stream-btn').forEach(b => b.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    let url = stream.url;

    // AES DECRYPTION LOGIC
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
        } catch(e) {
            console.error("Decryption failed", e);
        }
    }

    const box = document.getElementById('iframeBox');
    const old = box.querySelector('iframe');
    if(old) old.remove();

    if(!url) {
        box.innerHTML += '<div style="color:red;padding:20px;">Stream Unavailable (Error 404)</div>';
        return;
    }

    const frame = document.createElement('iframe');
    frame.setAttribute('allow', 'autoplay; fullscreen; encrypted-media; picture-in-picture');
    frame.setAttribute('scrolling', 'no');
    frame.style.width = '100%';
    frame.style.height = '100%';
    frame.style.border = 'none';
    frame.src = url;
    
    box.appendChild(frame);
}

window.closeStreamModal = function() {
    document.getElementById('streamModal').style.display = 'none';
    const f = document.querySelector('#iframeBox iframe');
    if(f) f.remove();
    history.pushState({}, "", "/");
};
