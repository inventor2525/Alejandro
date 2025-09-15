const socket = io();
let mediaRecorder;

async function startRecording() {
	console.log("startRecording clicked");
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
    mediaRecorder.start(500); // Send chunks every 500ms
    socket.emit("start_listening", {
		session_id:localStorage.getItem('sessionId'),
		mime_type: mediaRecorder.mimeType
	});
	console.log("startRecording sent");
}

function stopRecording() {
	console.log("stopRecording clicked");
    if (mediaRecorder) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        setTimeout(() => {
            socket.emit("stop_recording");
        }, 1000); // Wait 1000ms for final chunk to be sent
		console.log("stopRecording sent");
    }
}
document.getElementById("startButton").addEventListener("click", startRecording);
document.getElementById("stopButton").addEventListener("click", stopRecording);