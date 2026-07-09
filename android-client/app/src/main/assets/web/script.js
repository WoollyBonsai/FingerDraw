const isLocalApp = window.location.protocol === 'file:' || window.location.protocol === 'android-app:';

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
const sio = (isLocalApp || typeof io === 'undefined') ? { emit: () => {}, on: () => {} } : io();
const wsUrl = isLocalApp ? null : `ws://${window.location.host}/ws/video`;
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

    if (isLocalApp) return;
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
    const rect = inkCanvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
        xNorm: Math.max(0, Math.min(1, x / rect.width)),
        yNorm: Math.max(0, Math.min(1, y / rect.height))
    };
}

// Block context menu to fix Android long press
window.addEventListener('contextmenu', e => e.preventDefault());

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
        const canvasX = (touch.clientX - rect.left) * (inkCanvas.width / rect.width);
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
        const canvasX = (touch.clientX - rect.left) * (inkCanvas.width / rect.width);
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

// ==========================================
// NOTEBOOK LOGIC (IndexedDB + Optimistic UI)
// ==========================================

let dbPromise = null;
if (window.idb) {
    dbPromise = idb.openDB('notebook-store', 2, {
        upgrade(db, oldVersion) {
            if (!db.objectStoreNames.contains('notes')) {
                db.createObjectStore('notes', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('training')) {
                db.createObjectStore('training', { keyPath: 'id' });
            }
        },
    });
}

const noteListEl = document.getElementById('noteList');
const noteTitleEl = document.getElementById('noteTitle');
const inkCanvas = document.getElementById('inkCanvas');
const inkCtx = inkCanvas.getContext('2d');
let currentNoteId = null;
let saveTimeout = null;

// Ink Engine State
let strokes = []; // Array of { points: [[x,y,p]], color, size, tool }
let currentColor = '#000000';
let currentTool = 'pen'; // 'pen', 'eraser', 'line', 'rect', 'circle'
let currentThickness = 8;
let rulerActive = false;
let protractorActive = false;
let currentPenStyle = 'marker';
let currentBg = 'blank';

// Infinite Canvas Camera
let camera = { x: 0, y: 0, z: 1 };

// UI Nav
const sidebar = document.getElementById('notebookSidebar');
const overlay = document.getElementById('sidebarOverlay');

function toggleSidebar() {
    sidebar.classList.toggle('sidebar-hidden');
    overlay.style.display = sidebar.classList.contains('sidebar-hidden') ? 'none' : 'block';
}

document.getElementById('btnToggleSidebar').onclick = toggleSidebar;
overlay.onclick = toggleSidebar;

// Hide sidebar initially
sidebar.classList.add('sidebar-hidden');
overlay.style.display = 'none';

document.getElementById('btnStartNotebook').onclick = () => {
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('notebookDashboardScreen').style.display = 'flex';
    sio.emit('get_active_users');
    loadNotes();
};

document.getElementById('btnDashboardBack').onclick = () => {
    document.getElementById('notebookDashboardScreen').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'flex';
};

document.getElementById('btnNotebookDisconnect').onclick = () => {
    if (currentNoteId) {
        sio.emit('notebook_leave', currentNoteId);
        currentNoteId = null;
    }
    document.getElementById('notebookScreen').style.display = 'none';
    document.getElementById('notebookDashboardScreen').style.display = 'flex';
    sio.emit('get_active_users');
};

document.getElementById('btnNotebookExit').onclick = document.getElementById('btnNotebookDisconnect').onclick;

// Toolbar Handlers
document.querySelectorAll('.color-swatch').forEach(swatch => {
    swatch.onclick = (e) => {
        document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
        e.target.classList.add('active');
        currentColor = e.target.getAttribute('data-color');
        document.getElementById('toolPen').click();
    };
});

document.getElementById('toolPen').onclick = (e) => {
    currentTool = 'pen';
    setActiveToolBtn('toolPen');
    document.getElementById('toolEraser').classList.remove('eraser-active');
};
document.getElementById('toolEraser').onclick = (e) => {
    currentTool = 'eraser';
    setActiveToolBtn('toolEraser');
    document.getElementById('toolEraser').classList.add('eraser-active');
};
document.getElementById('toolLine').onclick = () => {
    currentTool = 'line';
    setActiveToolBtn('toolLine');
    document.getElementById('toolEraser').classList.remove('eraser-active');
};
document.getElementById('toolRect').onclick = () => {
    currentTool = 'rect';
    setActiveToolBtn('toolRect');
    document.getElementById('toolEraser').classList.remove('eraser-active');
};
document.getElementById('toolCircle').onclick = () => {
    currentTool = 'circle';
    setActiveToolBtn('toolCircle');
    document.getElementById('toolEraser').classList.remove('eraser-active');
};
document.getElementById('toolRuler').onclick = () => {
    rulerActive = !rulerActive;
    const widget = document.getElementById('rulerWidget');
    if (rulerActive) {
        document.getElementById('toolRuler').classList.add('active');
        widget.style.display = 'block';
    } else {
        document.getElementById('toolRuler').classList.remove('active');
        widget.style.display = 'none';
    }
};

document.getElementById('toolProtractor').onclick = () => {
    protractorActive = !protractorActive;
    const widget = document.getElementById('protractorWidget');
    if (protractorActive) {
        document.getElementById('toolProtractor').classList.add('active');
        widget.style.display = 'block';
    } else {
        document.getElementById('toolProtractor').classList.remove('active');
        widget.style.display = 'none';
    }
};

// Widget Dragging & Rotation State
function initWidget(widgetId, handleId) {
    const widget = document.getElementById(widgetId);
    const handle = document.getElementById(handleId);
    let dragging = false, rotating = false;
    let offsetX = 0, offsetY = 0;
    let angle = 0, cx = 0, cy = 0;
    
    widget.onpointerdown = (e) => {
        if (e.target === handle) return;
        dragging = true;
        widget.setPointerCapture(e.pointerId);
        const rect = widget.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
    };
    handle.onpointerdown = (e) => {
        e.stopPropagation();
        rotating = true;
        handle.setPointerCapture(e.pointerId);
        const rect = widget.getBoundingClientRect();
        cx = rect.left + rect.width / 2;
        cy = rect.top + rect.height / 2;
    };
    window.addEventListener('pointermove', (e) => {
        if (dragging) {
            const parentRect = document.getElementById('notebookEditor').getBoundingClientRect();
            const rawL = e.clientX - parentRect.left - offsetX;
            const rawT = e.clientY - parentRect.top - offsetY;
            widget.style.left = rawL + 'px';
            widget.style.top = rawT + 'px';
            widget.dataset.rawLeft = rawL;
            widget.dataset.rawTop = rawT;
        } else if (rotating) {
            const dx = e.clientX - cx;
            const dy = e.clientY - cy;
            angle = Math.atan2(dy, dx) * 180 / Math.PI;
            // Snap to 15 degrees for convenience
            if (e.shiftKey) angle = Math.round(angle / 15) * 15;
            widget.style.transform = `rotate(${angle}deg)`;
            widget.dataset.angle = angle;
            
            if (widgetId === 'protractorWidget') {
                const display = document.getElementById('protractorAngleDisplay');
                if (display) display.innerText = Math.round(angle) + '°';
            }
        }
    });
    window.addEventListener('pointerup', (e) => {
        if (dragging) {
            dragging = false;
            widget.releasePointerCapture(e.pointerId);
        }
        if (rotating) {
            rotating = false;
            handle.releasePointerCapture(e.pointerId);
        }
    });
}
initWidget('protractorWidget', 'protractorRotateHandle');
initWidget('rulerWidget', 'rulerRotateHandle');

document.getElementById('penStyle').onchange = (e) => {
    currentPenStyle = e.target.value;
};

function updateCursor() {
    if (currentTool === 'eraser') {
        const size = currentThickness * 2;
        const svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg"><circle cx="${size/2}" cy="${size/2}" r="${size/2 - 1}" fill="rgba(255,100,100,0.3)" stroke="red" stroke-width="1"/></svg>`;
        const url = `url(data:image/svg+xml;base64,${btoa(svg)}) ${size/2} ${size/2}, auto`;
        inkCanvas.style.cursor = url;
    } else if (['line', 'rect', 'circle'].includes(currentTool)) {
        inkCanvas.style.cursor = 'crosshair';
    } else {
        inkCanvas.style.cursor = 'crosshair';
    }
}

function setActiveToolBtn(id) {
    const ids = ['toolPen', 'toolEraser', 'toolLine', 'toolRect', 'toolCircle'];
    ids.forEach(bid => document.getElementById(bid).classList.remove('active'));
    document.getElementById(id).classList.add('active');
    updateCursor();
}

document.getElementById('penThickness').oninput = (e) => {
    currentThickness = parseInt(e.target.value);
    updateCursor();
};

document.getElementById('customColorPicker').oninput = (e) => {
    currentColor = e.target.value;
    document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
    // Optionally create a new swatch or just use the color
    const customSwatch = document.createElement('div');
    customSwatch.className = 'color-swatch active';
    customSwatch.style.background = currentColor;
    customSwatch.setAttribute('data-color', currentColor);
    customSwatch.onclick = (ev) => {
        document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
        ev.target.classList.add('active');
        currentColor = ev.target.getAttribute('data-color');
        document.getElementById('toolPen').click();
    };
    document.getElementById('colorPicker').insertBefore(customSwatch, document.getElementById('customColorPicker'));
    document.getElementById('toolPen').click();
};
document.getElementById('bgSelect').onchange = (e) => {
    currentBg = e.target.value;
    sio.emit('notebook_action', {
        note_id: currentNoteId,
        action: 'update_bg',
        payload: currentBg
    });
    triggerSave();
    redrawCanvas();
};

function resizeInkCanvas() {
    const wrapper = document.getElementById('notebookCanvasWrapper');
    if (!wrapper || wrapper.clientWidth === 0) return;
    const dpr = window.devicePixelRatio || 1;
    inkCanvas.width = wrapper.clientWidth * dpr;
    inkCanvas.height = wrapper.clientHeight * dpr;
    redrawCanvas();
}
const wrapperObserver = new ResizeObserver(() => {
    if (document.getElementById('notebookScreen').style.display === 'flex') {
        resizeInkCanvas();
    }
});
wrapperObserver.observe(document.getElementById('notebookCanvasWrapper'));

window.addEventListener('resize', () => {
    if (document.getElementById('notebookScreen').style.display === 'flex') {
        resizeInkCanvas();
    }
});

// Drawing Logic
const getStroke = window.perfectFreehand ? window.perfectFreehand.getStroke : null;

function drawStroke(ctx, strokeObj) {
    if (strokeObj.tool === 'eraser') return; // Rendered strokes only
    
    if (strokeObj.tool === 'pen' || !strokeObj.tool) {
        if (!getStroke) return;
        
        let thinning = 0.6;
        let smoothing = 0.7;
        let streamline = 0.7;
        let alpha = 1.0;
        
        ctx.shadowBlur = 0; // reset
        
        if (strokeObj.penStyle === 'pencil') {
            thinning = 0.2;
            smoothing = 0.4;
            alpha = 0.6;
        } else if (strokeObj.penStyle === 'brush') {
            thinning = 0.9;
            smoothing = 0.9;
            streamline = 0.9;
            alpha = 0.9;
        } else if (strokeObj.penStyle === 'crayon') {
            thinning = 0.1;
            smoothing = 0.3;
            alpha = 0.8;
            ctx.shadowBlur = 3;
            ctx.shadowColor = strokeObj.color;
        } else if (strokeObj.penStyle === 'marker') {
            thinning = -0.3;
            smoothing = 0.8;
            streamline = 0.6;
            alpha = 0.9;
        }
        
        const outline = getStroke(strokeObj.points, {
            size: strokeObj.size || 8,
            thinning,
            smoothing,
            streamline,
            simulatePressure: true
        });
        
        if (outline.length === 0) return;
        
        ctx.globalAlpha = alpha;
        ctx.fillStyle = strokeObj.color;
        ctx.beginPath();
        ctx.moveTo(outline[0][0], outline[0][1]);
        for (let i = 1; i < outline.length; i++) {
            ctx.lineTo(outline[i][0], outline[i][1]);
        }
        ctx.fill();
        ctx.globalAlpha = 1.0;
    } else {
        // Shapes
        if (strokeObj.points.length < 2) return;
        const start = strokeObj.points[0];
        const end = strokeObj.points[strokeObj.points.length - 1];
        
        ctx.strokeStyle = strokeObj.color;
        ctx.lineWidth = strokeObj.size || 8;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        
        if (strokeObj.tool === 'line') {
            ctx.moveTo(start[0], start[1]);
            ctx.lineTo(end[0], end[1]);
        } else if (strokeObj.tool === 'rect') {
            ctx.rect(start[0], start[1], end[0] - start[0], end[1] - start[1]);
        } else if (strokeObj.tool === 'circle') {
            const r = Math.hypot(end[0] - start[0], end[1] - start[1]);
            ctx.arc(start[0], start[1], r, 0, 2 * Math.PI);
        } else if (strokeObj.tool === 'polygon') {
            ctx.moveTo(strokeObj.points[0][0], strokeObj.points[0][1]);
            for (let i = 1; i < strokeObj.points.length; i++) {
                ctx.lineTo(strokeObj.points[i][0], strokeObj.points[i][1]);
            }
        }
        ctx.stroke();
    }
}

function drawBackground() {
    const dpr = window.devicePixelRatio || 1;
    const canvasWidth = inkCanvas.width / dpr;
    const canvasHeight = inkCanvas.height / dpr;

    inkCtx.fillStyle = '#ffffff';
    inkCtx.fillRect(0, 0, canvasWidth, canvasHeight);
    
    inkCtx.save();
    
    // Draw grid based on camera transformation
    const gridSize = 40 * camera.z;
    const offsetX = camera.x % gridSize;
    const offsetY = camera.y % gridSize;
    
    inkCtx.lineWidth = 1;
    if (currentBg === 'ruled') {
        inkCtx.strokeStyle = '#e0e0e0';
        for (let y = offsetY; y < canvasHeight; y += gridSize) {
            if (y < 0) continue;
            inkCtx.beginPath(); inkCtx.moveTo(0, y); inkCtx.lineTo(canvasWidth, y); inkCtx.stroke();
        }
    } else if (currentBg === 'grid') {
        inkCtx.strokeStyle = '#e0e0e0';
        for (let y = offsetY; y < canvasHeight; y += gridSize) {
            if (y < 0) continue;
            inkCtx.beginPath(); inkCtx.moveTo(0, y); inkCtx.lineTo(canvasWidth, y); inkCtx.stroke();
        }
        for (let x = offsetX; x < canvasWidth; x += gridSize) {
            if (x < 0) continue;
            inkCtx.beginPath(); inkCtx.moveTo(x, 0); inkCtx.lineTo(x, canvasHeight); inkCtx.stroke();
        }
    } else if (currentBg === 'dots') {
        inkCtx.fillStyle = '#c0c0c0';
        for (let y = offsetY; y < canvasHeight; y += gridSize) {
            if (y < 0) continue;
            for (let x = offsetX; x < canvasWidth; x += gridSize) {
                if (x < 0) continue;
                inkCtx.beginPath(); inkCtx.arc(x, y, 2, 0, Math.PI*2); inkCtx.fill();
            }
        }
    }
    inkCtx.restore();
}

function redrawCanvas() {
    drawBackground();
    
    inkCtx.save();
    const dpr = window.devicePixelRatio || 1;
    inkCtx.scale(dpr, dpr);
    inkCtx.translate(camera.x, camera.y);
    inkCtx.scale(camera.z, camera.z);
    
    for (const s of strokes) {
        drawStroke(inkCtx, s);
    }
    if (currentInkStroke) {
        drawStroke(inkCtx, currentInkStroke);
    }
    for (const s of Object.values(liveStrokes)) {
        drawStroke(inkCtx, s);
    }
    inkCtx.restore();
    drawMinimap();
}

function drawMinimap() {
    const minimapCanvas = document.getElementById('minimapCanvas');
    if (!minimapCanvas) return;
    const mCtx = minimapCanvas.getContext('2d');
    
    mCtx.clearRect(0, 0, minimapCanvas.width, minimapCanvas.height);
    
    // Determine bounding box of all strokes
    let minX = 0, minY = 0, maxX = inkCanvas.width, maxY = inkCanvas.height;
    if (strokes.length > 0) {
        let first = true;
        for (const s of strokes) {
            for (const p of s.points) {
                if (first) { minX = p[0]; maxX = p[0]; minY = p[1]; maxY = p[1]; first = false; }
                else {
                    if (p[0] < minX) minX = p[0];
                    if (p[0] > maxX) maxX = p[0];
                    if (p[1] < minY) minY = p[1];
                    if (p[1] > maxY) maxY = p[1];
                }
            }
        }
    }
    
    // Include current view in bounds
    const viewLeft = -camera.x / camera.z;
    const viewTop = -camera.y / camera.z;
    const viewRight = viewLeft + inkCanvas.width / camera.z;
    const viewBottom = viewTop + inkCanvas.height / camera.z;
    
    minX = Math.min(minX, viewLeft);
    minY = Math.min(minY, viewTop);
    maxX = Math.max(maxX, viewRight);
    maxY = Math.max(maxY, viewBottom);
    
    // Add margin
    const margin = 100;
    minX -= margin; minY -= margin; maxX += margin; maxY += margin;
    
    const worldW = maxX - minX;
    const worldH = maxY - minY;
    
    const scale = Math.min(minimapCanvas.width / worldW, minimapCanvas.height / worldH);
    
    mCtx.save();
    // Center it
    mCtx.translate(minimapCanvas.width/2 - (worldW*scale)/2, minimapCanvas.height/2 - (worldH*scale)/2);
    mCtx.scale(scale, scale);
    mCtx.translate(-minX, -minY);
    
    // Draw strokes
    for (const s of strokes) { drawStroke(mCtx, s); }
    if (currentInkStroke) drawStroke(mCtx, currentInkStroke);
    for (const s of Object.values(liveStrokes)) { drawStroke(mCtx, s); }
    
    // Draw viewport rect
    mCtx.strokeStyle = 'rgba(231, 76, 60, 0.8)';
    mCtx.lineWidth = 2 / scale;
    mCtx.strokeRect(viewLeft, viewTop, inkCanvas.width / camera.z, inkCanvas.height / camera.z);
    
    mCtx.restore();
}

// Input Handlers for Canvas (Pan, Zoom, Infinite Canvas, Long-Press Eraser, Palm Rejection)
let activePointers = new Map();
let drawingPointerId = null;
let longPressTimeout = null;
let smartShapeTimeout = null;
let tempEraserMode = false;
let initialPinchDist = null;
let initialCamera = null;
let lastPanCenter = null;
let liveStrokes = {}; // strokes being drawn by others

function getScreenCoords(e) {
    const rect = inkCanvas.getBoundingClientRect();
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        pressure: e.pressure !== undefined && e.pressure !== 0 ? e.pressure : 0.5
    };
}

function getWorldCoords(screenX, screenY) {
    return {
        x: (screenX - camera.x) / camera.z,
        y: (screenY - camera.y) / camera.z
    };
}

function getPinchCenter(p1, p2) {
    return { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
}

function getPinchDistance(p1, p2) {
    return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function handlePointerDown(e) {
    if (e.pointerType !== 'mouse' && e.pointerType !== 'pen' && e.pointerType !== 'touch') return;

    
    inkCanvas.setPointerCapture(e.pointerId);
    activePointers.set(e.pointerId, getScreenCoords(e));
    
    if (activePointers.size === 1) {
        // Start Drawing or Long Press
        drawingPointerId = e.pointerId;
        tempEraserMode = false;
        
        const sc = activePointers.get(e.pointerId);
        const wc = getWorldCoords(sc.x, sc.y);
        
        currentInkStroke = {
            id: Math.random().toString(36).substr(2, 9),
            tool: currentTool,
            penStyle: currentTool === 'pen' ? currentPenStyle : null,
            color: currentColor,
            size: currentThickness / camera.z,
            points: [[wc.x, wc.y, sc.pressure]]
        };
        
        // Long Press Eraser gesture
        longPressTimeout = setTimeout(() => {
            if (activePointers.size === 1 && currentInkStroke) {
                // Check if moved too much
                let movedTooMuch = false;
                const p0 = currentInkStroke.points[0];
                for(let i=1; i<currentInkStroke.points.length; i++) {
                    const p = currentInkStroke.points[i];
                    if (Math.hypot(p[0] - p0[0], p[1] - p0[1]) * camera.z > 15) {
                        movedTooMuch = true;
                        break;
                    }
                }
                if (!movedTooMuch) {
                // Not much movement, switch to temp eraser
                tempEraserMode = true;
                document.getElementById('toolEraser').classList.add('eraser-active');
                currentInkStroke = null;
                redrawCanvas();
                }
            }
        }, 500);
        
    } else if (activePointers.size === 2) {
        // Switch to Pan/Zoom mode
        drawingPointerId = null;
        clearTimeout(longPressTimeout);
        clearTimeout(smartShapeTimeout);
        currentInkStroke = null; // Cancel stroke
        
        const pts = Array.from(activePointers.values());
        initialPinchDist = getPinchDistance(pts[0], pts[1]);
        lastPanCenter = getPinchCenter(pts[0], pts[1]);
        initialCamera = { ...camera };
    }
}

function handlePointerMove(e) {
    if (!activePointers.has(e.pointerId)) return;
    activePointers.set(e.pointerId, getScreenCoords(e));
    
    if (activePointers.size === 1 && drawingPointerId === e.pointerId) {
        const sc = activePointers.get(e.pointerId);
        const wc = getWorldCoords(sc.x, sc.y);
        
        // If moved significantly, cancel long press
        if (currentInkStroke && currentInkStroke.points.length > 5) {
            clearTimeout(longPressTimeout);
        }
        
        const activeTool = tempEraserMode ? 'eraser' : currentTool;
        
        if (activeTool === 'eraser') {
            const eraserRadiusSq = (currentThickness / camera.z) ** 2;
            strokes = strokes.filter(s => {
                if (!s.points || s.points.length === 0) return false;
                if (s.points.length === 1) {
                    return (s.points[0][0] - wc.x)**2 + (s.points[0][1] - wc.y)**2 > eraserRadiusSq;
                }
                for (let i = 0; i < s.points.length - 1; i++) {
                    const x1 = s.points[i][0], y1 = s.points[i][1];
                    const x2 = s.points[i+1][0], y2 = s.points[i+1][1];
                    const l2 = (x2 - x1)**2 + (y2 - y1)**2;
                    let distSq;
                    if (l2 === 0) {
                        distSq = (wc.x - x1)**2 + (wc.y - y1)**2;
                    } else {
                        let t = ((wc.x - x1) * (x2 - x1) + (wc.y - y1) * (y2 - y1)) / l2;
                        t = Math.max(0, Math.min(1, t));
                        distSq = (wc.x - (x1 + t * (x2 - x1)))**2 + (wc.y - (y1 + t * (y2 - y1)))**2;
                    }
                    if (distSq < eraserRadiusSq) return false; // erase
                }
                return true; // keep
            });
            redrawCanvas();
        } else if (currentInkStroke) {
            let px = wc.x;
            let py = wc.y;
            
            if (rulerActive || protractorActive) {
                const parentRect = document.getElementById('notebookEditor').getBoundingClientRect();
                const widget = document.getElementById(rulerActive ? 'rulerWidget' : 'protractorWidget');
                
                // Get raw untransformed pos (fallback to parsing style or 30%)
                let rawL = parseFloat(widget.dataset.rawLeft);
                let rawT = parseFloat(widget.dataset.rawTop);
                if (isNaN(rawL)) rawL = parentRect.width * 0.3; // 30% left
                if (isNaN(rawT)) rawT = parentRect.height * (rulerActive ? 0.4 : 0.3); // 40% or 30% top
                
                const angle = parseFloat(widget.dataset.angle || 0) * Math.PI / 180;
                
                // Un-transformed center in screen coords
                let cx, cy;
                if (rulerActive) {
                    cx = parentRect.left + rawL + 250; // width 500
                    cy = parentRect.top + rawT + 30; // height 60
                } else {
                    cx = parentRect.left + rawL + 150; // width 300
                    cy = parentRect.top + rawT + 150; // height 150 (origin bottom center)
                }
                
                const dx = sc.x - cx;
                const dy = sc.y - cy;
                const rx = dx * Math.cos(-angle) - dy * Math.sin(-angle);
                const ry = dx * Math.sin(-angle) + dy * Math.cos(-angle);
                
                let newRx = rx;
                let newRy = ry;
                
                if (rulerActive) {
                    // Snap to top (-30) or bottom (+30) edge
                    newRy = Math.abs(ry + 30) < Math.abs(ry - 30) ? -30 : 30;
                } else if (protractorActive) {
                    // Snap to semi-circle radius 150
                    const dist = Math.hypot(rx, ry);
                    if (ry <= 0 && dist > 50) {
                        // Project onto circle edge
                        newRx = rx / dist * 150;
                        newRy = ry / dist * 150;
                    } else if (ry > 0) {
                        // Snapped to bottom flat edge of protractor
                        newRy = 0;
                    }
                }
                
                const finalDx = newRx * Math.cos(angle) - newRy * Math.sin(angle);
                const finalDy = newRx * Math.sin(angle) + newRy * Math.cos(angle);
                
                const snapWc = getWorldCoords(cx + finalDx, cy + finalDy);
                px = snapWc.x;
                py = snapWc.y;
            }
            
            currentInkStroke.points.push([px, py, sc.pressure]);
            
            // Smart shape hold-to-snap logic
            if (currentInkStroke.tool === 'pen') {
                clearTimeout(smartShapeTimeout);
                smartShapeTimeout = setTimeout(() => {
                    if (drawingPointerId !== null && currentInkStroke && currentInkStroke.tool === 'pen' && currentInkStroke.points.length > 10) {
                        detectAndSnapShape();
                    }
                }, 600);
            }

            // Throttle network events by sending live updates roughly every 3 points
            if (currentInkStroke.points.length % 3 === 0) {
                sio.emit('notebook_action', {
                    note_id: currentNoteId,
                    action: 'live_stroke',
                    payload: currentInkStroke
                });
            }
            redrawCanvas();
        }
        
    } else if (activePointers.size === 2) {
        // Handle Pan/Zoom
        const pts = Array.from(activePointers.values());
        const currentDist = getPinchDistance(pts[0], pts[1]);
        const currentCenter = getPinchCenter(pts[0], pts[1]);
        
        if (initialPinchDist > 0) {
            const zoomFactor = currentDist / initialPinchDist;
            let newZ = initialCamera.z * zoomFactor;
            newZ = Math.max(0.1, Math.min(newZ, 10)); // Clamp zoom
            
            // Zoom towards the original pinch center
            const dx = currentCenter.x - lastPanCenter.x;
            const dy = currentCenter.y - lastPanCenter.y;
            
            camera.x += dx;
            camera.y += dy;
            
            // Adjust for scale center
            const zoomRatio = newZ / camera.z;
            camera.x = currentCenter.x - (currentCenter.x - camera.x) * zoomRatio;
            camera.y = currentCenter.y - (currentCenter.y - camera.y) * zoomRatio;
            camera.z = newZ;
            
            lastPanCenter = currentCenter;
            redrawCanvas();
        }
    }
}

function handlePointerUp(e) {
    if (!activePointers.has(e.pointerId)) return;
    activePointers.delete(e.pointerId);
    inkCanvas.releasePointerCapture(e.pointerId);
    
    if (e.pointerId === drawingPointerId) {
        clearTimeout(longPressTimeout);
        clearTimeout(smartShapeTimeout);
        if (!tempEraserMode && currentTool !== 'eraser' && currentInkStroke && currentInkStroke.points.length > 0) {
            strokes.push(currentInkStroke);
            sio.emit('notebook_action', {
                note_id: currentNoteId,
                action: 'add_stroke',
                payload: currentInkStroke
            });
        } else if (currentTool === 'eraser' || tempEraserMode) {
            sio.emit('notebook_action', {
                note_id: currentNoteId,
                action: 'set_strokes',
                payload: strokes
            });
        }
        currentInkStroke = null;
        drawingPointerId = null;
        if (tempEraserMode) {
            document.getElementById('toolEraser').classList.remove('eraser-active');
        }
        tempEraserMode = false;
        triggerSave();
        redrawCanvas();
    }
    
    if (activePointers.size < 2) {
        initialPinchDist = null;
        initialCamera = null;
        lastPanCenter = null;
    }
    
    // If we dropped to 1 pointer from 2, we shouldn't immediately start drawing with it.
    // We'll let the user lift and touch again to draw.
    if (activePointers.size === 1) {
        drawingPointerId = null; 
    }
}

function simplifyPath(points, epsilon) {
    if (points.length < 3) return points;
    
    // Find the point with the maximum distance
    let dmax = 0;
    let index = 0;
    const end = points.length - 1;
    
    for (let i = 1; i < end; i++) {
        const d = pointLineDistance(points[i], points[0], points[end]);
        if (d > dmax) {
            index = i;
            dmax = d;
        }
    }
    
    // If max distance is greater than epsilon, recursively simplify
    if (dmax > epsilon) {
        const recResults1 = simplifyPath(points.slice(0, index + 1), epsilon);
        const recResults2 = simplifyPath(points.slice(index), epsilon);
        return recResults1.slice(0, recResults1.length - 1).concat(recResults2);
    } else {
        return [points[0], points[end]];
    }
}

function pointLineDistance(p, a, b) {
    const num = Math.abs((b[1] - a[1]) * p[0] - (b[0] - a[0]) * p[1] + b[0] * a[1] - b[1] * a[0]);
    const den = Math.hypot(b[1] - a[1], b[0] - a[0]);
    if (den === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
    return num / den;
}

function detectAndSnapShape() {
    if (!currentInkStroke || currentInkStroke.tool !== 'pen' || currentInkStroke.points.length < 10) return;
    
    const pts = currentInkStroke.points;
    const start = pts[0];
    const end = pts[pts.length - 1];
    
    // Calculate bounding box
    let minX = start[0], maxX = start[0], minY = start[1], maxY = start[1];
    for (const p of pts) {
        if (p[0] < minX) minX = p[0];
        if (p[0] > maxX) maxX = p[0];
        if (p[1] < minY) minY = p[1];
        if (p[1] > maxY) maxY = p[1];
    }
    const width = maxX - minX;
    const height = maxY - minY;
    
    const distStartEnd = Math.hypot(end[0] - start[0], end[1] - start[1]);
    const maxDimension = Math.max(width, height);
    const epsilon = maxDimension * 0.12;
    
    // Simplify the path to detect corners
    const simplified = simplifyPath(pts, epsilon);
    
    // Is it closed? (start and end are close relative to its size)
    if (distStartEnd < maxDimension * 0.3) {
        if (simplified.length >= 3 && simplified.length <= 4) { // Triangle
            currentInkStroke.tool = 'polygon';
            // Snap the last point to the first point to close it perfectly
            simplified[simplified.length - 1] = simplified[0];
            currentInkStroke.points = simplified;
        } else {
            // Check if it's roughly square/circular
            const aspectRatio = Math.max(width, height) / Math.max(Math.min(width, height), 1);
            if (aspectRatio > 0 && aspectRatio < 1.6 && simplified.length > 5) {
                // Convert to Circle
                currentInkStroke.tool = 'circle';
                const cx = minX + width / 2;
                const cy = minY + height / 2;
                currentInkStroke.points = [[cx, cy, 0], [cx + Math.max(width, height) / 2, cy, 0]];
            } else {
                // Convert to Rect or Polygon
                if (simplified.length === 5) { // 4 corners + 1 close
                    currentInkStroke.tool = 'polygon';
                    simplified[simplified.length - 1] = simplified[0];
                    currentInkStroke.points = simplified;
                } else {
                    currentInkStroke.tool = 'rect';
                    currentInkStroke.points = [[minX, minY, 0], [maxX, maxY, 0]];
                }
            }
        }
    } else {
        // It's open. Check if it is straight line or zigzag
        let pathLength = 0;
        for (let i = 1; i < pts.length; i++) {
            pathLength += Math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1]);
        }
        
        if (distStartEnd > pathLength * 0.8 && simplified.length <= 3) { 
            // fairly straight
            currentInkStroke.tool = 'line';
            currentInkStroke.points = [start, end];
        } else if (simplified.length > 2) {
            // Zigzag or polyline
            currentInkStroke.tool = 'polygon';
            currentInkStroke.points = simplified;
        }
    }
    
    redrawCanvas();
}

inkCanvas.addEventListener('pointerdown', handlePointerDown);
inkCanvas.addEventListener('pointermove', handlePointerMove);
inkCanvas.addEventListener('pointerup', handlePointerUp);
inkCanvas.addEventListener('pointercancel', handlePointerUp);
inkCanvas.addEventListener('pointerout', (e) => {
    // Treat out same as up, except if it's captured it shouldn't trigger out usually
    handlePointerUp(e);
});
// Prevent default wheel behavior (like scrolling page) and use for zooming
inkCanvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (e.ctrlKey) {
        // Zoom
        const zoomDelta = Math.exp(-e.deltaY * 0.01);
        const newZ = Math.max(0.1, Math.min(camera.z * zoomDelta, 10));
        const zoomRatio = newZ / camera.z;
        const rect = inkCanvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        
        camera.x = mx - (mx - camera.x) * zoomRatio;
        camera.y = my - (my - camera.y) * zoomRatio;
        camera.z = newZ;
    } else {
        // Pan
        camera.x -= e.deltaX;
        camera.y -= e.deltaY;
    }
    redrawCanvas();
}, { passive: false });


// Data Layer
let allNotesCache = [];
async function loadNotes() {
    if(!dbPromise) return;
    const db = await dbPromise;
    let notes = [];
    try {
        const res = await fetch('/api/notebook/notes/');
        notes = await res.json();
        const tx = db.transaction('notes', 'readwrite');
        for (const n of notes) {
            tx.store.put(n);
        }
        await tx.done;
    } catch (e) {
        console.log("Offline, loading from cache", e);
        notes = await db.getAll('notes');
    }
    allNotesCache = notes;
    const searchInput = document.getElementById('dashboardSearch');
    if (!searchInput || !searchInput.value.trim()) {
        renderNoteList(notes);
    }
}

let activeUsersCounts = {};

sio.on('active_users_update', (counts) => {
    activeUsersCounts = counts;
    loadNotes(); // Re-render lists to update badges
});

sio.on('notebook_action', (data) => {
    if (data.note_id !== currentNoteId) return;
    if (data.action === 'add_stroke') {
        if (data.payload.id) delete liveStrokes[data.payload.id];
        strokes.push(data.payload);
        redrawCanvas();
    } else if (data.action === 'set_strokes') {
        strokes = data.payload;
        redrawCanvas();
    } else if (data.action === 'live_stroke') {
        liveStrokes[data.payload.id] = data.payload;
        redrawCanvas();
    } else if (data.action === 'update_bg') {
        currentBg = data.payload;
        document.getElementById('bgSelect').value = currentBg;
        redrawCanvas();
    }
});

function renderNoteList(notes) {
    noteListEl.innerHTML = '';
    const gridEl = document.getElementById('dashboardGrid');
    if (gridEl) gridEl.innerHTML = '';
    
    notes.sort((a,b) => new Date(b.updated_at) - new Date(a.updated_at));
    notes.forEach(note => {
        // Sidebar list
        const li = document.createElement('li');
        li.innerText = note.title || 'Untitled';
        li.onclick = () => selectNote(note.id);
        if (note.id === currentNoteId) li.classList.add('active');
        noteListEl.appendChild(li);
        
        // Dashboard Card
        if (gridEl) {
            const card = document.createElement('div');
            card.className = 'dashboard-card';
            card.onclick = () => selectNote(note.id);
            
            const activeCount = activeUsersCounts[note.id] || 0;
            const badgeHtml = activeCount > 0 
                ? `<div class="users-badge">${activeCount} active user${activeCount > 1 ? 's' : ''}</div>`
                : '';
                
            card.innerHTML = `
                <div>
                    <h3>${note.title || 'Untitled'}</h3>
                    <div class="date">Updated: ${new Date(note.updated_at).toLocaleDateString()}</div>
                </div>
                ${badgeHtml}
            `;
            gridEl.appendChild(card);
        }
    });
}

let searchTimeout = null;
const searchInput = document.getElementById('dashboardSearch');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        clearTimeout(searchTimeout);
        
        if (!val) {
            renderNoteList(allNotesCache);
            return;
        }
        
        searchTimeout = setTimeout(async () => {
            try {
                // First do a local text search on titles
                const localMatches = allNotesCache.filter(n => n.title && n.title.toLowerCase().includes(val.toLowerCase()));
                
                // Update UI instantly with local matches so old content disappears
                if (localMatches.length === 0) {
                    document.getElementById('dashboardGrid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 20px;">Searching OCR...</div>';
                } else {
                    renderNoteList(localMatches);
                }
                
                // Then try to fetch from vector store (OCR / semantic)
                const res = await fetch('/api/notebook/search/?query=' + encodeURIComponent(val));
                const searchData = await res.json();
                
                let matchedIds = new Set(localMatches.map(n => n.id));
                if (searchData && searchData.results && searchData.results.ids && searchData.results.ids.length > 0) {
                    const ids = searchData.results.ids[0];
                    const distances = (searchData.results.distances && searchData.results.distances.length > 0) ? searchData.results.distances[0] : [];
                    ids.forEach((id, idx) => {
                        // Chroma default embedding distance: < 1.3 is generally a good match
                        if (distances.length === 0 || distances[idx] < 1.3) {
                            matchedIds.add(id);
                        }
                    });
                }
                
                const finalNotes = allNotesCache.filter(n => matchedIds.has(n.id));
                if (finalNotes.length === 0) {
                    document.getElementById('dashboardGrid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 20px;">No notebooks found matching "'+val+'"</div>';
                } else {
                    renderNoteList(finalNotes);
                }
            } catch (err) {
                console.error("Search failed, falling back to local only", err);
                const localM = allNotesCache.filter(n => n.title && n.title.toLowerCase().includes(val.toLowerCase()));
                if (localM.length === 0) {
                    document.getElementById('dashboardGrid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 20px;">No notebooks found matching "'+val+'"</div>';
                } else {
                    renderNoteList(localM);
                }
            }
        }, 500);
    });
}

async function selectNote(id) {
    if(!dbPromise) return;
    currentNoteId = id;
    const db = await dbPromise;
    const note = await db.get('notes', id);
    if (note) {
        noteTitleEl.value = note.title;
        try {
            const data = JSON.parse(note.content || '{}');
            strokes = data.strokes || [];
            currentBg = data.bg || 'blank';
            camera = data.camera || { x: 0, y: 0, z: 1 };
            document.getElementById('bgSelect').value = currentBg;
        } catch(e) {
            strokes = [];
            camera = { x: 0, y: 0, z: 1 };
        }
    }
    // Show Screen
    document.getElementById('notebookDashboardScreen').style.display = 'none';
    document.getElementById('notebookScreen').style.display = 'flex';
    
    sio.emit('notebook_join', id);
    
    resizeInkCanvas();
    setTimeout(resizeInkCanvas, 50);
    // Hide sidebar on mobile/tablet after selection
    if (window.innerWidth < 768) {
        sidebar.classList.add('sidebar-hidden');
        overlay.style.display = 'none';
    }
    const notes = await db.getAll('notes');
    renderNoteList(notes);
}

document.getElementById('btnDashboardNew').onclick = async () => {
    const newId = 'temp-' + Date.now();
    const newNote = {
        id: newId,
        title: 'New Note',
        content: JSON.stringify({strokes: [], bg: 'blank', camera: {x:0, y:0, z:1}}),
        updated_at: new Date().toISOString(),
        isTemp: true
    };
    if(dbPromise) {
        const db = await dbPromise;
        await db.put('notes', newNote);
        const notes = await db.getAll('notes');
        renderNoteList(notes);
        selectNote(newId);
    }
};

document.getElementById('btnNewNote').onclick = document.getElementById('btnDashboardNew').onclick;

// Editor Auto-Save
function triggerSave() {
    if (!currentNoteId) return;
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(syncNote, 1000);
}
noteTitleEl.addEventListener('input', triggerSave);

async function syncNote() {
    if (!currentNoteId || !dbPromise) return;
    const title = noteTitleEl.value;
    const content = JSON.stringify({ strokes, bg: currentBg, camera });
    const db = await dbPromise;
    
    let note = await db.get('notes', currentNoteId);
    if (!note) return;
    
    note.title = title;
    note.content = content;
    note.updated_at = new Date().toISOString();
    await db.put('notes', note);
    
    const notes = await db.getAll('notes');
    renderNoteList(notes);
    
    try {
        const image = document.getElementById('inkCanvas').toDataURL("image/png");
        const enable_ocr = document.getElementById('ocrToggle').checked;
        const payload = { title, content, tags: "", image, enable_ocr };
        let res;
        if (note.isTemp) {
            res = await fetch('/api/notebook/notes/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            res = await fetch(`/api/notebook/notes/${currentNoteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }
        if (res.ok) {
            const savedNote = await res.json();
            if (note.isTemp) {
                await db.delete('notes', currentNoteId);
                await db.put('notes', savedNote);
                currentNoteId = savedNote.id;
            } else {
                await db.put('notes', savedNote);
            }
        }
    } catch (e) {
        console.log("Offline mode: changes saved locally.", e);
    }
}


