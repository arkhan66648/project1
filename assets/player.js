// assets/player.js

window.initPlayer = function(matchData, isLocked) {
    // Update global current match for unlockStream reference
    window.currentMatchData = matchData; 

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
        // Update URL safely
        history.pushState({}, "", `/watch/${matchData.id}`);
    }
};

function loadIframeStream(stream, btnElement) {
    // UI Updates
    document.querySelectorAll('.stream-btn').forEach(b => b.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    // Decode Logic
    let url = stream.url;
    if(stream.encrypted_data) { 
        try { 
            // Simple Base64 decode fallback
            url = window.atob(stream.encrypted_data.split(':')[1]); 
        } catch(e){ console.warn("Decode error", e); } 
    }

    // Embed Iframe
    const box = document.getElementById('iframeBox');
    const old = box.querySelector('iframe');
    if(old) old.remove();

    const frame = document.createElement('iframe');
    frame.setAttribute('allow', 'autoplay; fullscreen; encrypted-media; picture-in-picture');
    frame.setAttribute('scrolling', 'no');
    frame.style.width = '100%';
    frame.style.height = '100%';
    frame.style.border = 'none';
    frame.src = url;
    
    box.appendChild(frame);
}

// Global Close Function
window.closeStreamModal = function() {
    document.getElementById('streamModal').style.display = 'none';
    const f = document.querySelector('#iframeBox iframe');
    if(f) f.remove();
    history.pushState({}, "", "/");
};
