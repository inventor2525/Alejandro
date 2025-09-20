// Initialize session ID
if (!localStorage.getItem('sessionId') || window.location.pathname === '/') {
    localStorage.setItem('sessionId', window.initialSessionId);
}
window.sessionId = localStorage.getItem('sessionId');
window.name = 'alejandro_main'; // Used to open this window back up by name from other tabs

class ReconnectingEventSource {
    constructor(url) {
        this.url = url;
        this.listeners = {};
        this.reconnectInterval = 1000;
        this.reconnectAttempts = 0;
        this.connect();
    }

    addEventListener(type, listener) {
        if (!this.listeners[type]) {
            this.listeners[type] = [];
        }
        this.listeners[type].push(listener);
        if (this.es && this.es.readyState !== 2) { // 2 is CLOSED
            this.es.addEventListener(type, listener);
        }
    }

    removeEventListener(type, listener) {
        if (this.listeners[type]) {
            this.listeners[type] = this.listeners[type].filter(l => l !== listener);
            if (this.es) {
                this.es.removeEventListener(type, listener);
            }
        }
    }

    syncScreen() {
        let screen_url = window.location.pathname.substring(1);
        if (screen_url.endsWith('/')) {
            screen_url = screen_url.slice(0, -1);
        }
        return fetch(`/sync_screen`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: window.sessionId,
                screen_url: screen_url
            })
        }).then(response => {
            if (!response.ok) {
                throw new Error('Sync screen failed');
            }
            return response.json();
        });
    }

    connect() {
        this.syncScreen()
            .then(() => {
                this.es = new EventSource(this.url);
                
                this.es.addEventListener('open', () => {
                    console.log('SSE connected');
                    this.reconnectAttempts = 0;
                });

                this.es.addEventListener('error', (err) => {
                    console.error('SSE error:', err);
                    this.es.close();
                    this.reconnectAttempts++;
                    setTimeout(() => this.connect(), this.reconnectInterval * this.reconnectAttempts);
                });

                // Re-attach listeners
                for (const type in this.listeners) {
                    this.listeners[type].forEach(listener => {
                        this.es.addEventListener(type, listener);
                    });
                }
            })
            .catch(err => {
                console.error('Sync screen error:', err);
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), this.reconnectInterval * this.reconnectAttempts);
            });
    }
}

// Handle control clicks
function triggerControl(controlId) {
    const button = document.getElementById(controlId);
    simulateButtonClick(button);
    
    fetch(`/control`, {
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
const eventSource = new ReconnectingEventSource(`/event_stream?session=${window.sessionId}`);

eventSource.addEventListener('message', function(event) {
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
});

// Open recorder tab
function openRecorder() {
    const sessionId = localStorage.getItem('sessionId');
    const url = '/recorder?session=' + sessionId;
    localStorage.setItem('alejandro_main_url', window.location.pathname);
    openOrFocus(url, 'alejandro_recorder');
}