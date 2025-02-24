// Debounce helper
let lastClick = 0;
const DEBOUNCE_MS = 500;

// Handle control clicks
function triggerControl(controlId) {
    const now = Date.now();
    if (now - lastClick < DEBOUNCE_MS) {
        console.log('Debouncing rapid click');
        return;
    }
    lastClick = now;

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
    
    switch(data.type) {
        case 'TranscriptionEvent':
            document.getElementById('transcription-text').textContent = data.text;
            break;
        case 'NavigationEvent':
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
