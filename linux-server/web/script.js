const player = document.getElementById('player');
const overlayCanvas = document.getElementById('overlayCanvas');
const overlayCtx = overlayCanvas.getContext('2d');
const wrapper = document.getElementById('canvas-wrapper');
const container = document.getElementById('canvas-container');

let isPenMode = false;
let isAltPressed = false;
let jmuxer = null;

// UI Setup
document.getElementById('btnPointer').onclick = (e) => {
    isPenMode = false;
    e.target.classList.add('active');
    document.getElementById('btnPen').classList.remove('active');
};
document.getElementById('btnPen').onclick = (e) => {
    isPenMode = true;
    e.target.classList.add('active');
    document.getElementById('btnPointer').classList.remove('active');
};
document.getElementById('btnAlt').onclick = (e) => {
    isAltPressed = !isAltPressed;
    e.target.classList.toggle('active');
    sio.emit('input_command', `ALT:${isAltPressed ? 1 : 0}`);
};
document.getElementById('btnMeta').onclick = () => sio.emit('input_command', 'META');
document.getElementById('btnTab').onclick = () => sio.emit('input_command', 'TAB');
document.getElementById('btnFullscreen').onclick = toggleFullscreen;

document.getElementById('btnDisconnect').onclick = () => {
    sio.emit('disconnect_request');
    if (ws) { ws.close(); ws = null; }
    if (jmuxer) { jmuxer.destroy(); jmuxer = null; }
    if (document.fullscreenElement) {
        document.exitFullscreen().catch(()=>{});
    }
    
    document.getElementById('welcomeScreen').style.display = 'flex';
    document.getElementById('appScreen').style.display = 'none';
};

document.getElementById('btnStartStream').onclick = () => {
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('appScreen').style.display = 'flex';
    
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(()=>{});
    }
    
    sio.emit('start_web_stream');
    connectVideo();
};

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(()=>{});
    } else {
        if (document.exitFullscreen) document.exitFullscreen();
    }
}

// Ensure fullscreen exits elegantly back to welcome screen if they exit via hardware back button
document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement && document.getElementById('appScreen').style.display === 'flex') {
        // Only trigger disconnect if they manually exited via OS (not clicking our disconnect button)
        // Actually, we shouldn't force disconnect, just let them be not-fullscreen.
    }
});

// Networking
const sio = io();
const wsUrl = `ws://${window.location.host}/ws/video`;
let ws = null;

function connectVideo() {
    if (jmuxer) {
        jmuxer.destroy();
    }
    
    jmuxer = new JMuxer({
        node: 'player',
        mode: 'video',
        flushingTime: 0,
        fps: 60,
        debug: false
    });

    if (ws) ws.close();
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    
    ws.onmessage = (event) => {
        jmuxer.feed({ video: new Uint8Array(event.data) });
    };
    
    ws.onclose = () => {
        if (document.getElementById('appScreen').style.display === 'flex') {
            setTimeout(connectVideo, 1000);
        }
    };
}

// Layout sizing
function updateLayout() {
    if (player.videoWidth > 0 && player.videoHeight > 0) {
        if (overlayCanvas.width !== player.videoWidth || overlayCanvas.height !== player.videoHeight) {
            overlayCanvas.width = player.videoWidth;
            overlayCanvas.height = player.videoHeight;
        }
        
        const containerAspect = container.clientWidth / container.clientHeight;
        const videoAspect = player.videoWidth / player.videoHeight;
        
        if (containerAspect > videoAspect) {
            wrapper.style.height = '100%';
            wrapper.style.width = `${container.clientHeight * videoAspect}px`;
        } else {
            wrapper.style.width = '100%';
            wrapper.style.height = `${container.clientWidth / videoAspect}px`;
        }
    }
}
player.addEventListener('resize', updateLayout);
window.addEventListener('resize', updateLayout);

// Zoom & Pan State
let transformScale = 1.0;
let transformX = 0;
let transformY = 0;

function updateTransform() {
    wrapper.style.transformOrigin = '0 0';
    wrapper.style.transform = `translate(${transformX}px, ${transformY}px) scale(${transformScale})`;
}

// Trail Logic
let currentStroke = [];
let fadingStrokes = [];

function addTrailPoint(x, y) { 
    currentStroke.push({x, y}); 
}

function drawTrail() {
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    const now = Date.now();
    
    // Draw current stroke
    if (currentStroke.length >= 2) {
        overlayCtx.beginPath();
        overlayCtx.moveTo(currentStroke[0].x, currentStroke[0].y);
        for(let i=1; i<currentStroke.length; i++) overlayCtx.lineTo(currentStroke[i].x, currentStroke[i].y);
        
        overlayCtx.strokeStyle = `rgba(0, 255, 0, 0.6)`;
        overlayCtx.lineWidth = 10;
        overlayCtx.lineCap = 'round';
        overlayCtx.lineJoin = 'round';
        overlayCtx.stroke();
    }
    
    // Draw fading strokes
    fadingStrokes = fadingStrokes.filter(s => now - s.t < 400);
    fadingStrokes.forEach(s => {
        if (s.points.length >= 2) {
            overlayCtx.beginPath();
            overlayCtx.moveTo(s.points[0].x, s.points[0].y);
            for(let i=1; i<s.points.length; i++) overlayCtx.lineTo(s.points[i].x, s.points[i].y);
            
            const alpha = Math.max(0, 1 - (now - s.t)/400);
            overlayCtx.strokeStyle = `rgba(0, 255, 0, ${alpha * 0.6})`;
            overlayCtx.lineWidth = 10;
            overlayCtx.lineCap = 'round';
            overlayCtx.lineJoin = 'round';
            overlayCtx.stroke();
        }
    });
    
    requestAnimationFrame(drawTrail);
}
drawTrail();

// Touch Handling
function getNormCoords(clientX, clientY) {
    const rect = overlayCanvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
        xNorm: Math.max(0, Math.min(1, x / rect.width)),
        yNorm: Math.max(0, Math.min(1, y / rect.height))
    };
}

let isFourFingerSwiping = false;
let swipeStartX = 0, swipeStartY = 0;

let isPanning = false;
let lastPanPoint = null;

let initialPinchDistance = null;
let initialScale = 1.0;
let initialPinchCenter = {x: 0, y: 0};
let initialTransform = {x: 0, y: 0};

overlayCanvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if (e.touches.length === 4) {
        isFourFingerSwiping = true;
        swipeStartX = e.touches[0].clientX;
        swipeStartY = e.touches[0].clientY;
        return;
    }
    
    if (e.touches.length === 2) {
        // Start 2-finger zoom/pan
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        initialPinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
        initialScale = transformScale;
        initialPinchCenter = {
            x: (t1.clientX + t2.clientX) / 2,
            y: (t1.clientY + t2.clientY) / 2
        };
        initialTransform = {x: transformX, y: transformY};
        
        isPanning = false;
        if (isPenMode) {
             sio.emit('input_command', `U`);
             if (currentStroke.length > 0) {
                 fadingStrokes.push({ points: currentStroke, t: Date.now() });
                 currentStroke = [];
             }
        }
        return;
    }
    
    if (!isPenMode && e.touches.length === 1) {
        isPanning = true;
        lastPanPoint = {x: e.touches[0].clientX, y: e.touches[0].clientY};
    }
    
    if (isPenMode && e.touches.length === 1) {
        const touch = e.touches[0];
        const {xNorm, yNorm} = getNormCoords(touch.clientX, touch.clientY);
        const pressure = touch.force || 1.0; 
        sio.emit('input_command', `D:${xNorm},${yNorm},${pressure}`);
        
        const rect = overlayCanvas.getBoundingClientRect();
        const canvasX = (touch.clientX - rect.left) * (overlayCanvas.width / rect.width);
        const canvasY = (touch.clientY - rect.top) * (overlayCanvas.height / rect.height);
        
        currentStroke = [{x: canvasX, y: canvasY}];
    }
}, {passive: false});

overlayCanvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    
    if (isFourFingerSwiping && e.touches.length === 4) {
        const dx = e.touches[0].clientX - swipeStartX;
        const dy = e.touches[0].clientY - swipeStartY;
        if (Math.abs(dx) > 150) {
            sio.emit('input_command', dx > 0 ? 'SWIPE4:RIGHT' : 'SWIPE4:LEFT');
            isFourFingerSwiping = false;
        } else if (Math.abs(dy) > 150) {
            sio.emit('input_command', dy > 0 ? 'SWIPE4:DOWN' : 'SWIPE4:UP');
            isFourFingerSwiping = false;
        }
        return;
    }
    
    if (e.touches.length === 2 && initialPinchDistance != null) {
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        const currentDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
        const currentCenter = {
            x: (t1.clientX + t2.clientX) / 2,
            y: (t1.clientY + t2.clientY) / 2
        };
        
        const scaleRatio = (currentDistance / initialPinchDistance);
        let newScale = initialScale * scaleRatio;
        newScale = Math.max(0.2, Math.min(newScale, 5.0));
        const actualScaleRatio = newScale / initialScale;
        
        transformX = currentCenter.x - (initialPinchCenter.x - initialTransform.x) * actualScaleRatio;
        transformY = currentCenter.y - (initialPinchCenter.y - initialTransform.y) * actualScaleRatio;
        transformScale = newScale;
        
        updateTransform();
        return;
    }
    
    if (!isPenMode && e.touches.length === 1 && isPanning) {
        const dx = e.touches[0].clientX - lastPanPoint.x;
        const dy = e.touches[0].clientY - lastPanPoint.y;
        transformX += dx;
        transformY += dy;
        lastPanPoint = {x: e.touches[0].clientX, y: e.touches[0].clientY};
        updateTransform();
    }
    
    if (isPenMode && e.touches.length === 1) {
        const touch = e.touches[0];
        const {xNorm, yNorm} = getNormCoords(touch.clientX, touch.clientY);
        const pressure = touch.force || 1.0;
        sio.emit('input_command', `M:${xNorm},${yNorm},${pressure}`);
        
        const rect = overlayCanvas.getBoundingClientRect();
        const canvasX = (touch.clientX - rect.left) * (overlayCanvas.width / rect.width);
        const canvasY = (touch.clientY - rect.top) * (overlayCanvas.height / rect.height);
        addTrailPoint(canvasX, canvasY);
    }
}, {passive: false});

overlayCanvas.addEventListener('touchend', (e) => {
    e.preventDefault();
    if (e.touches.length < 4) isFourFingerSwiping = false;
    if (e.touches.length < 2) initialPinchDistance = null;
    
    if (!isPenMode && e.touches.length === 0) {
        isPanning = false;
    }
    
    if (isPenMode && e.touches.length === 0) {
        sio.emit('input_command', `U`);
        if (currentStroke.length > 0) {
            fadingStrokes.push({ points: currentStroke, t: Date.now() });
            currentStroke = [];
        }
    }
}, {passive: false});

// Mouse fallback
let isMouseDown = false;
overlayCanvas.addEventListener('mousedown', (e) => {
    if(!isPenMode) {
        isPanning = true;
        lastPanPoint = {x: e.clientX, y: e.clientY};
        return;
    }
    isMouseDown = true;
    const {xNorm, yNorm} = getNormCoords(e.clientX, e.clientY);
    sio.emit('input_command', `D:${xNorm},${yNorm},1.0`);
});
window.addEventListener('mousemove', (e) => {
    if(!isPenMode && isPanning) {
        const dx = e.clientX - lastPanPoint.x;
        const dy = e.clientY - lastPanPoint.y;
        transformX += dx;
        transformY += dy;
        lastPanPoint = {x: e.clientX, y: e.clientY};
        updateTransform();
        return;
    }
    if(!isPenMode || !isMouseDown) return;
    const {xNorm, yNorm} = getNormCoords(e.clientX, e.clientY);
    sio.emit('input_command', `M:${xNorm},${yNorm},1.0`);
});
window.addEventListener('mouseup', () => {
    isPanning = false;
    if(!isPenMode || !isMouseDown) return;
    isMouseDown = false;
    sio.emit('input_command', `U`);
});

