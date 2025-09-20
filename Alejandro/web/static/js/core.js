// Initialize session ID
if (!localStorage.getItem('sessionId') || window.location.pathname === '/') {
    localStorage.setItem('sessionId', window.initialSessionId);
}
window.sessionId = localStorage.getItem('sessionId');
window.name = 'alejandro_main'; // Used to open this window back up by name from other tabs

// Handle control clicks
function triggerControl(controlId) {
    const button = document.getElementById(controlId);
    simulateButtonClick(button);
    
    const host = window.location.hostname;
    const port = window.location.port;
    fetch(`http://${host}:${port}/control`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            control_id: controlId,
            session_id: localStorage.getItem('sessionId'),
            window_path:window.location.pathname
        })
    })
    .then(response => {
        console.log('Control response:', response);
        return response.json();
    })
    .catch(error => {
        console.error('Control error:', error);
    });
}

// Animate button clicks
function simulateButtonClick(button) {
    button.classList.add('clicked');
    setTimeout(() => {
        button.classList.remove('clicked');
    }, 500);
}

// Setup SSE for transcriptions and actions
// Use same host as page for EventSource
const host = window.location.hostname;
const port = window.location.port;
const eventSource = new EventSource(`http://${host}:${port}/event_stream?session=${window.sessionId}`);

eventSource.onmessage = function(event) {
    if (!event.data) {
        return; // Skip keepalive
    }

    try {
        console.log('Received event data:', event.data);
        
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'TranscriptionEvent':
                const transcriptionElement = document.getElementById('transcription-text');
                if (transcriptionElement) {
                    transcriptionElement.textContent = data.text;
                }
                break;
            case 'NavigationEvent':
                const targetUrl = '/' + data.screen + '?session=' + data.session_id;
                console.log('Navigating to:', data.screen, ' at ', targetUrl);
                window.location.href = targetUrl;
                break;
            // Terminal events are handled directly by terminal.js's event listener
            // Don't process them here to avoid duplication
        }
    } catch (e) {
        console.error('Error processing event:', e);
    }
};

// eventSource.onerror = function() {
//     console.log('SSE connection failed, reconnecting...');
//     setTimeout(() => {
//         window.location.reload();
//     }, 1000);
// };

// Open recorder tab
function openRecorder() {
    const sessionId = localStorage.getItem('sessionId');
    const url = '/recorder?session=' + sessionId;
    localStorage.setItem('alejandro_main_url', window.location.pathname);
    openOrFocus(url, 'alejandro_recorder');
}