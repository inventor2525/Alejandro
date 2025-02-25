// Initialize session ID
if (!localStorage.getItem('sessionId')) {
    localStorage.setItem('sessionId', window.initialSessionId);
}
window.sessionId = localStorage.getItem('sessionId');

// Handle control clicks
function triggerControl(controlId) {
    const button = document.getElementById(controlId);
    simulateButtonClick(button);
    
    fetch('/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            control_id: controlId,
            session_id: window.sessionId
        })
    })
    .then(response => {
        console.log('Control response:', response);
        return response.json();
    })
    .then(data => {
        console.log('Control data:', data);
        if (data.screen) {
            window.location.href = '/' + data.screen + '?session=' + window.sessionId;
        }
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
const eventSource = new EventSource(`http://${host}:5000/stream?session=${window.sessionId}`);

eventSource.onmessage = function(event) {
    if (!event.data) {
        console.log('Skipping keepalive');
        return;
    }
    
    console.log('Raw SSE event:', event);
    console.log('Event data:', event.data);
    
    const data = JSON.parse(event.data);
    console.log('Parsed event data:', data);
    
    switch(data.type) {
        case 'TranscriptionEvent':
            document.getElementById('transcription-text').textContent = data.text;
            break;
        case 'NavigationEvent':
            console.log('Navigating to:', data.screen);
            if (data.force || window.location.pathname.substring(1) !== data.screen) {
                window.location.href = '/' + data.screen + '?session=' + window.sessionId;
                window.location.reload();
            }
            break;
    }
};

eventSource.onerror = function() {
    console.log('SSE connection failed, reconnecting...');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
};
