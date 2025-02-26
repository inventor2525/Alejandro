// Initialize xterm.js
let term;
let fitAddon;
let terminalReady = false;
let pendingData = [];

// Initialize terminal
function initTerminal() {
    // Create terminal instance
    term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#000000',
            foreground: '#ffffff'
        },
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        fontSize: 14,
        lineHeight: 1.2,
        scrollback: 1000
    });

    // Add addons
    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon.WebLinksAddon());

    // Open terminal
    term.open(document.getElementById('terminal-container'));
    fitAddon.fit();

    // Handle terminal input
    term.onData(data => {
        sendTerminalInput(data);
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (fitAddon) {
            fitAddon.fit();
        }
    });

    // Mark terminal as ready
    terminalReady = true;
    
    // Process any pending data
    if (pendingData.length > 0) {
        pendingData.forEach(data => {
            term.write(data);
        });
        pendingData = [];
    }
    
    // Send a dummy input to initialize the terminal if needed
    sendTerminalInput('\r');
}

// Send terminal input to server
function sendTerminalInput(data) {
    const host = window.location.hostname;
    const port = window.location.port;
    fetch(`http://${host}:${port}/terminal/input`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: window.sessionId,
            terminal_id: window.terminalId,
            input: data
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Terminal input response:', data);
    })
    .catch(error => {
        console.error('Error sending terminal input:', error);
    });
}

// Switch between terminals
function switchTerminal(terminalId) {
    if (terminalId === window.terminalId) {
        return; // Already on this terminal
    }
    
    window.terminalId = terminalId;
    console.log('Switching to terminal:', terminalId);
    
    // Update URL without reloading
    const url = new URL(window.location.href);
    url.searchParams.set('terminal_id', terminalId);
    window.history.pushState({}, '', url);
    
    // Clear terminal and request new data
    if (term) {
        term.clear();
    }
    
    // Update active tab
    document.querySelectorAll('.terminal-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.textContent.trim() === terminalId) {
            tab.classList.add('active');
        }
    });
    
    // Send a dummy input to refresh the terminal
    sendTerminalInput('\r');
}

// Handle terminal data from server
function handleTerminalData(data) {
    if (data.terminal_id !== window.terminalId) {
        return; // Skip updates for other terminals
    }
    
    if (!terminalReady) {
        // Queue data until terminal is ready
        pendingData.push(data.raw_text);
        return;
    }
    
    // Clear and write new content
    term.write(data.raw_text);
}

// Override the existing event source handler
window.addEventListener('load', function() {
    // Initialize terminal
    initTerminal();
    
    // Make sure we have the terminal ID
    console.log('Terminal page loaded with terminal ID:', window.terminalId);
    
    // Override the event source handler
    eventSource.onmessage = function(event) {
        if (!event.data) {
            return; // Skip keepalive
        }
        
        try {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'TranscriptionEvent':
                    document.getElementById('transcription-text').textContent = data.text;
                    break;
                case 'NavigationEvent':
                    console.log('Navigation event received:', data.screen);
                    const targetUrl = '/' + data.screen + '?session=' + data.session_id;
                    if (window.location.pathname !== '/' + data.screen) {
                        window.location.href = targetUrl;
                    }
                    break;
                case 'TerminalScreenEvent':
                    console.log('Terminal event received for:', data.terminal_id);
                    // If we don't have a terminal ID yet, use the one from the event
                    if (!window.terminalId && data.terminal_id) {
                        window.terminalId = data.terminal_id;
                        console.log('Setting terminal ID to:', window.terminalId);
                    }
                    handleTerminalData(data);
                    break;
            }
        } catch (e) {
            console.error('Error processing event:', e);
        }
    };
});
