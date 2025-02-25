// Initialize session ID
if (!localStorage.getItem('sessionId') || window.location.pathname === '/') {
    localStorage.setItem('sessionId', window.initialSessionId);
}
window.sessionId = localStorage.getItem('sessionId');

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
            session_id: localStorage.getItem('sessionId')
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
const port = window.location.port;
const eventSource = new EventSource(`http://${host}:${port}/stream?session=${window.sessionId}`);

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
            if (data.force || window.location.pathname.substring(1) !== data.screen + 'screen') {
                window.location.href = '/' + data.screen + '?session=' + data.session_id;
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
