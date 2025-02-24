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
    .then(response => response.json())
    .then(data => {
        if (data.navigate) {
            window.location.href = '/' + data.navigate + '?session=' + window.sessionId;
        }
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
