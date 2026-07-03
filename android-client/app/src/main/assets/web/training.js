// Handwriting Training Logic
const trainingChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?,.=-+";
let currentTrainIndex = 0;
let trainingStrokes = [];
let currentTrainStroke = null;
const trainCanvas = document.getElementById('trainingCanvas');
let trainCtx = null;

if (trainCanvas) {
    trainCtx = trainCanvas.getContext('2d');
    
    // Resize correctly
    const resizeTrainCanvas = () => {
        const rect = trainCanvas.parentElement.getBoundingClientRect();
        trainCanvas.width = rect.width;
        trainCanvas.height = rect.height;
        drawTrainCanvas();
    };
    window.addEventListener('resize', resizeTrainCanvas);
    
    document.getElementById('btnTrainHandwriting').onclick = () => {
        document.getElementById('notebookDashboardScreen').style.display = 'none';
        document.getElementById('trainingScreen').style.display = 'flex';
        setTimeout(resizeTrainCanvas, 100);
        updateTrainingUI();
    };
    document.getElementById('btnTrainingBack').onclick = () => {
        document.getElementById('trainingScreen').style.display = 'none';
        document.getElementById('notebookDashboardScreen').style.display = 'flex';
    };
    
    trainCanvas.onpointerdown = (e) => {
        trainCanvas.setPointerCapture(e.pointerId);
        const rect = trainCanvas.getBoundingClientRect();
        currentTrainStroke = { points: [[e.clientX - rect.left, e.clientY - rect.top, e.pressure || 0.5]] };
    };
    trainCanvas.onpointermove = (e) => {
        if (!currentTrainStroke) return;
        const rect = trainCanvas.getBoundingClientRect();
        currentTrainStroke.points.push([e.clientX - rect.left, e.clientY - rect.top, e.pressure || 0.5]);
        drawTrainCanvas();
    };
    trainCanvas.onpointerup = (e) => {
        if (!currentTrainStroke) return;
        trainCanvas.releasePointerCapture(e.pointerId);
        trainingStrokes.push(currentTrainStroke);
        currentTrainStroke = null;
        drawTrainCanvas();
    };
    
    document.getElementById('btnTrainingClear').onclick = () => {
        trainingStrokes = [];
        drawTrainCanvas();
    };
    
    document.getElementById('btnTrainingNext').onclick = async () => {
        if (trainingStrokes.length === 0) {
            alert("Please draw the character before proceeding!");
            return;
        }
        
        // Save to indexedDB for now, or just pretend for UI
        // We will store it in local db under 'training'
        if (typeof dbPromise !== 'undefined' && dbPromise) {
            const db = await dbPromise;
            await db.put('training', { 
                id: trainingChars[currentTrainIndex], 
                char: trainingChars[currentTrainIndex], 
                strokes: trainingStrokes 
            });
        }
        
        trainingStrokes = [];
        currentTrainIndex++;
        if (currentTrainIndex >= trainingChars.length) {
            alert("Training complete! Your custom OCR profile is saved and ready.");
            document.getElementById('trainingScreen').style.display = 'none';
            document.getElementById('notebookDashboardScreen').style.display = 'flex';
            currentTrainIndex = 0;
        } else {
            updateTrainingUI();
            drawTrainCanvas();
        }
    };
}

function updateTrainingUI() {
    document.getElementById('trainingTargetChar').innerText = trainingChars[currentTrainIndex];
    document.getElementById('trainingProgressText').innerText = `${currentTrainIndex}/${trainingChars.length}`;
    document.getElementById('trainingProgressBar').style.width = `${(currentTrainIndex / trainingChars.length) * 100}%`;
}

function drawTrainCanvas() {
    if (!trainCtx) return;
    trainCtx.clearRect(0, 0, trainCanvas.width, trainCanvas.height);
    
    // Draw guide lines
    trainCtx.strokeStyle = '#eee';
    trainCtx.lineWidth = 2;
    trainCtx.beginPath();
    trainCtx.moveTo(0, trainCanvas.height / 2);
    trainCtx.lineTo(trainCanvas.width, trainCanvas.height / 2);
    trainCtx.moveTo(0, trainCanvas.height * 0.75);
    trainCtx.lineTo(trainCanvas.width, trainCanvas.height * 0.75);
    trainCtx.stroke();
    
    trainCtx.fillStyle = '#333';
    
    const strokesToDraw = [...trainingStrokes];
    if (currentTrainStroke) strokesToDraw.push(currentTrainStroke);
    
    for (const s of strokesToDraw) {
        // We assume getStroke and getSvgPathFromStroke are globally available from perfect-freehand
        if (typeof getStroke !== 'undefined') {
            const outline = getStroke(s.points, { size: 10, thinning: 0.6, smoothing: 0.7, streamline: 0.7 });
            const path = new Path2D(getSvgPathFromStroke(outline));
            trainCtx.fill(path);
        } else {
            // fallback if perfect-freehand isn't ready
            trainCtx.beginPath();
            if (s.points.length > 0) {
                trainCtx.moveTo(s.points[0][0], s.points[0][1]);
                for (let i = 1; i < s.points.length; i++) {
                    trainCtx.lineTo(s.points[i][0], s.points[i][1]);
                }
            }
            trainCtx.stroke();
        }
    }
}
