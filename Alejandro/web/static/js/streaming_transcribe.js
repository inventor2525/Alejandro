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
    mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
            // Send audio via HTTP POST instead of SocketIO to avoid payload limits
            const formData = new FormData();
            formData.append('session_id', localStorage.getItem('sessionId'));
            formData.append('audio_data', event.data);

            try {
                await fetch('/audio_chunk', {
                    method: 'POST',
                    body: formData
                });
            } catch (error) {
                console.error("Failed to send audio chunk:", error);
            }
        }
    };
    mediaRecorder.onstop = () => {
        toggleButtons(false);
    };
    mediaRecorder.start(2000); // Send chunks every 2000ms

    // Send start_listening via HTTP instead of SocketIO to avoid rate limits
    try {
        await fetch('/start_listening', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: localStorage.getItem('sessionId'),
                mime_type: mediaRecorder.mimeType
            })
        });
        console.log("startRecording sent via HTTP");
    } catch (error) {
        console.error("Failed to start listening:", error);
    }

    toggleButtons(true);
}

async function stopRecording() {
    console.log("stopRecording clicked");
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());

        // Wait for final chunk to be sent, then send stop via HTTP
        setTimeout(async () => {
            try {
                await fetch('/stop_listening', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: localStorage.getItem('sessionId')
                    })
                });
                console.log("stopRecording sent via HTTP");
            } catch (error) {
                console.error("Failed to stop listening:", error);
            }
        }, 1000);
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