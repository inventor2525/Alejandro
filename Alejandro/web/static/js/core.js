// Handle control clicks
function triggerControl(controlId) {
    const button = document.getElementById(controlId);
    simulateButtonClick(button);
    
    fetch(`/control/${controlId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.navigate) {
            window.location.href = '/' + data.navigate;
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
const eventSource = new EventSource('/stream');

eventSource.onmessage = function(event) {
    if (!event.data) return; // Skip keepalive
    
    const data = JSON.parse(event.data);
    
    if (data.text) {
        document.getElementById('transcription-text').textContent = data.text;
    }
    
    if (data.navigate) {
        window.location.href = '/' + data.navigate;
    }
};

eventSource.onerror = function() {
    console.log('SSE connection failed, reconnecting...');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
};
