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
        let url_params = new URLSearchParams(window.location.search);
        let extra_url_params = {};
        for (let [key, value] of url_params.entries()) {
            if (key !== 'session') {
                extra_url_params[key] = value;
            }
        }
        return fetch(`/sync_screen`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: window.sessionId,
                screen_url: screen_url,
                extra_url_params: extra_url_params
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
function triggerControl(controlId, fromPython = false) {
    const button = document.getElementById(controlId);
    simulateButtonClick(button);
    
    let function_arguments = {};
    const getterName = button.dataset.jsGetter;
    if (getterName && window[getterName]) {
        try {
            function_arguments = window[getterName]();
            if (typeof function_arguments !== 'object' || function_arguments === null) {
                throw new Error('Getter function must return an object');
            }
        } catch (error) {
            console.error('Error executing getter function:', error);
            return;
        }
    } else if (getterName) {
        console.error(`Getter function ${getterName} not found`);
        return;
    }
    
    let url_params = new URLSearchParams(window.location.search);
    let extra_url_params = {};
    for (let [key, value] of url_params.entries()) {
        if (key !== 'session') {
            extra_url_params[key] = value;
        }
    }
    
    fetch(`/control`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            control_id: controlId,
            session_id: localStorage.getItem('sessionId'),
            window_path:window.location.pathname,
            extra_url_params: extra_url_params,
            function_arguments: function_arguments,
            from_python: fromPython
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Control response:', data);
        const handlerName = button.dataset.jsReturnHandler;
        if (handlerName && window[handlerName]) {
            if (data.return_value) {
                try {
                    const returnValue = JSON.parse(data.return_value);
                    window[handlerName](returnValue);
                } catch (error) {
                    console.error('Error handling return value:', error);
                }
            }
            else {
                try {
                    window[handlerName]();
                } catch (error) {
                    console.error('Error handling callback function:', error);
                }
            }
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
                let targetUrl = '/' + data.screen + '?session=' + data.session_id;
                if (data.extra_url_params) {
                    Object.entries(data.extra_url_params).forEach(([key, value]) => {
                        targetUrl += (targetUrl.includes('?') ? '&' : '?') + key + '=' + value;
                    });
                }
                console.log('Navigating to:', data.screen, ' at ', targetUrl);
                window.location.href = targetUrl;
                break;
            case 'ControlTriggerEvent':
                triggerControl(data.control_id, true);
                break;
            case 'ControlReturnEvent':
                const button = document.getElementById(data.control_id);
                if (button) {
                    const handlerName = button.dataset.jsReturnHandler;
                    if (handlerName && window[handlerName] && data.return_value) {
                        try {
                            const returnValue = JSON.parse(data.return_value);
                            window[handlerName](returnValue);
                        } catch (error) {
                            console.error('Error handling return value:', error);
                        }
                    }
                }
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
    const url = window.location.origin + '/recorder?session=' + sessionId;
    localStorage.setItem('alejandro_main_url', window.location.href);
    openOrFocus(url, 'alejandro_recorder');
}