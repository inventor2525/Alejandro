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
const eventSource = new EventSource('/stream?session=' + window.sessionId);

eventSource.onmessage = function(event) {
    if (!event.data) return; // Skip keepalive
    
    const data = JSON.parse(event.data);
    
    console.log('Received event:', data);
    switch(data.type) {
        case 'TranscriptionEvent':
            document.getElementById('transcription-text').textContent = data.text;
            break;
        case 'NavigationEvent':
            console.log('Navigating to:', data.screen);
            window.location.href = '/' + data.screen + '?session=' + window.sessionId;
            break;
    }
};

eventSource.onerror = function() {
    console.log('SSE connection failed, reconnecting...');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
};
