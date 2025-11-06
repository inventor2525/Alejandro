const socket = io();
let mediaRecorder;

function toggleButtons(isRecording) {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    startButton.classList.toggle('hidden', isRecording);
    stopButton.classList.toggle('hidden', !isRecording);
}

async function startRecording() {
    console.log("startRecording clicked");
    if (mediaRecorder && mediaRecorder.state === 'recording') return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            socket.emit("audio_chunk", {
                session_id:localStorage.getItem('sessionId'),
                audio_data:event.data
            });
        }
    };
    mediaRecorder.onstop = () => {
        toggleButtons(false);
    };
    mediaRecorder.start(500); // Send chunks every 500ms
    socket.emit("start_listening", {
        session_id:localStorage.getItem('sessionId'),
        mime_type: mediaRecorder.mimeType
    });
    console.log("startRecording sent");
    toggleButtons(true);
}

function stopRecording() {
    console.log("stopRecording clicked");
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        setTimeout(() => {
            socket.emit("stop_listening", { session_id: localStorage.getItem('sessionId') });
        }, 1000); // Wait 1000ms for final chunk to be sent
        console.log("stopRecording sent");
    }
}

// Send manual text
function sendManual() {
    const text = document.getElementById('manualInput').value.trim();
    if (text) {
        socket.emit('manual_text_entry', { session_id: localStorage.getItem('sessionId'), text: text });
        document.getElementById('manualInput').value = '';
    }
}

// Open main tab with opener check
function openMain() {
    const mainUrl = localStorage.getItem('alejandro_main_url');
    openOrFocus(mainUrl, 'alejandro_main');
}

// Button listeners
document.getElementById("startButton").addEventListener("click", startRecording);
document.getElementById("stopButton").addEventListener("click", stopRecording);
document.getElementById("sendButton").addEventListener("click", sendManual);
document.getElementById("openMainButton").addEventListener("click", openMain);