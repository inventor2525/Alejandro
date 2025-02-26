// Initialize xterm.js
let term;
let fitAddon;
let terminalReady = false;
let pendingData = [];

// Initialize terminal
function initTerminal() {
    console.log("Initializing xterm.js terminal");
    
    // If terminal is already initialized, just return
    if (terminalReady && term) {
        console.log("Terminal already initialized, skipping initialization");
        return;
    }
    
    // Check if required libraries are loaded
    if (typeof Terminal === 'undefined') {
        console.error("xterm.js Terminal is not defined! Make sure the library is loaded.");
        document.getElementById('terminal-container').innerHTML = 
            '<div style="color: red; padding: 20px;">Error: xterm.js library not loaded properly.</div>';
        return;
    }
    
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

    console.log("Terminal instance created");

    // Add addons if available
    try {
        if (window.FitAddon) {
            fitAddon = new window.FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            console.log("Fit addon loaded");
        } else {
            console.warn("FitAddon not available");
        }
        
        if (window.WebLinksAddon) {
            term.loadAddon(new window.WebLinksAddon.WebLinksAddon());
            console.log("WebLinks addon loaded");
        } else {
            console.warn("WebLinksAddon not available");
        }
    } catch (e) {
        console.error("Error loading addons:", e);
    }

    // Get terminal container
    const container = document.getElementById('terminal-container');
    if (!container) {
        console.error("Terminal container not found!");
        return;
    }

    // Open terminal
    try {
        term.open(container);
        console.log("Terminal opened in container");
        
        if (fitAddon) {
            fitAddon.fit();
            console.log("Terminal fitted to container");
        }
    } catch (e) {
        console.error("Error opening terminal:", e);
        container.innerHTML = 
            `<div style="color: red; padding: 20px;">Error opening terminal: ${e.message}</div>`;
        return;
    }

    // Handle terminal input
    term.onData(data => {
        sendTerminalInput(data);
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (fitAddon) {
            fitAddon.fit();
            // Send terminal size to server
            const dimensions = term.options;
            sendTerminalResize(dimensions.cols, dimensions.rows);
        }
    });

    // Mark terminal as ready
    terminalReady = true;
    console.log("Terminal ready");

    // Restore buffer if available
    const savedBuffer = localStorage.getItem(`terminal_buffer_${window.terminalId}`);
    const savedCursor = localStorage.getItem(`terminal_cursor_${window.terminalId}`);

    if (savedBuffer) {
        try {
            const buffer = JSON.parse(savedBuffer);
            console.log(`Restoring terminal buffer for ${window.terminalId} (${buffer.length} lines)`);
        
            // Clear terminal first
            term.clear();
        
            // Write saved buffer
            buffer.forEach((line, index) => {
                if (index > 0) {
                    term.write('\r\n');
                }
                if (line) {
                    term.write(line);
                }
            });
        
            // Restore cursor position if available
            if (savedCursor) {
                const cursor = JSON.parse(savedCursor);
                term.write(`\x1b[${cursor.y};${cursor.x}H`);
            }
            
            // Set a flag to prevent server updates from overwriting our restored buffer
            localStorage.setItem(`terminal_restoring_${window.terminalId}`, 'true');
            
            // Clear the restoration flag after a short delay
            setTimeout(() => {
                localStorage.removeItem(`terminal_restoring_${window.terminalId}`);
                console.log("Terminal restoration complete, accepting server updates again");
            }, 1000);
        } catch (e) {
            console.error("Error restoring terminal buffer:", e);
        }
    } else {
        // Process any pending data if no saved buffer
        if (pendingData.length > 0) {
            console.log(`Processing ${pendingData.length} pending data items`);
            pendingData.forEach(data => {
                term.write(data);
            });
            pendingData = [];
        }
    }

    // Send terminal size to server
    if (fitAddon) {
        const dimensions = term.options;
        sendTerminalResize(dimensions.cols, dimensions.rows);
    }
    
    // No need to send initial input
    
    // Terminal is ready
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

// Send terminal resize to server
function sendTerminalResize(cols, rows) {
    const host = window.location.hostname;
    const port = window.location.port;
    fetch(`http://${host}:${port}/terminal/resize`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: window.sessionId,
            terminal_id: window.terminalId,
            cols: cols,
            rows: rows
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Terminal resize response:', data);
    })
    .catch(error => {
        console.error('Error sending terminal resize:', error);
    });
}

// Clear terminal
function clearTerminal() {
    if (term) {
        term.clear();
        // Also send clear command to server
        sendTerminalInput('\x1b[H\x1b[2J');
    }
}

// Save terminal buffer manually
function saveTerminalBuffer() {
    if (!term) return;
    
    const lines = term.buffer.active.getLines();
    const buffer = [];
    
    // Convert lines to strings
    for (let i = 0; i < lines.length; i++) {
        if (lines[i]) {
            buffer.push(lines[i].translateToString(true));
        }
    }
    
    // Store buffer and cursor position
    localStorage.setItem(`terminal_buffer_${window.terminalId}`, JSON.stringify(buffer));
    localStorage.setItem(`terminal_cursor_${window.terminalId}`, JSON.stringify({
        x: term.buffer.active.cursorX,
        y: term.buffer.active.cursorY
    }));
    console.log(`Manually saved terminal buffer for ${window.terminalId} (${buffer.length} lines)`);
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
    
    // Check if we have a saved buffer that we're restoring
    const isRestoringBuffer = localStorage.getItem(`terminal_buffer_${window.terminalId}`) !== null;
    
    // Only write data if we're not in the middle of restoring a buffer
    if (!isRestoringBuffer) {
        // Write new content directly to terminal
        term.write(data.raw_text);
    } else {
        console.log("Skipping server update while restoring buffer");
    }
}

// Store terminal state when navigating away
window.addEventListener('beforeunload', function(event) {
    // Only store state if we're on the terminal page
    if (window.location.pathname.includes('/terminal')) {
        console.log("Storing terminal state before navigation");
        localStorage.setItem('terminalActive', 'true');
        localStorage.setItem('lastTerminalId', window.terminalId);
        
        // Force save the terminal buffer
        if (term) {
            const lines = term.buffer.active.getLines();
            const buffer = [];
            
            // Convert lines to strings
            for (let i = 0; i < lines.length; i++) {
                if (lines[i]) {
                    buffer.push(lines[i].translateToString(true));
                }
            }
            
            // Store buffer and cursor position with a timestamp
            const timestamp = Date.now();
            localStorage.setItem(`terminal_buffer_${window.terminalId}`, JSON.stringify(buffer));
            localStorage.setItem(`terminal_cursor_${window.terminalId}`, JSON.stringify({
                x: term.buffer.active.cursorX,
                y: term.buffer.active.cursorY,
                timestamp: timestamp
            }));
            console.log(`Stored terminal buffer for ${window.terminalId} (${buffer.length} lines) at ${timestamp}`);
        }
    }
});

// Also store terminal state when clicking on navigation controls
document.addEventListener('click', function(event) {
    if (event.target.tagName === 'BUTTON' && 
        event.target.id !== 'new' && 
        event.target.id !== 'next' && 
        event.target.id !== 'prev' && 
        window.location.pathname.includes('/terminal')) {
        
        console.log("Navigation button clicked, saving terminal state");
        if (term) {
            const lines = term.buffer.active.getLines();
            const buffer = [];
            
            // Convert lines to strings
            for (let i = 0; i < lines.length; i++) {
                if (lines[i]) {
                    buffer.push(lines[i].translateToString(true));
                }
            }
            
            // Store buffer and cursor position
            localStorage.setItem(`terminal_buffer_${window.terminalId}`, JSON.stringify(buffer));
            localStorage.setItem(`terminal_cursor_${window.terminalId}`, JSON.stringify({
                x: term.buffer.active.cursorX,
                y: term.buffer.active.cursorY
            }));
            console.log(`Stored terminal buffer for ${window.terminalId} (${buffer.length} lines)`);
        }
    }
});

// Override the existing event source handler
window.addEventListener('load', function() {
    console.log("Terminal page load event fired");
    
    // Check if we're returning to the terminal page
    const wasTerminalActive = localStorage.getItem('terminalActive') === 'true';
    const lastTerminalId = localStorage.getItem('lastTerminalId');
    
    if (wasTerminalActive && lastTerminalId && window.terminalId !== lastTerminalId) {
        console.log(`Restoring previous terminal: ${lastTerminalId}`);
        window.terminalId = lastTerminalId;
        
        // Update URL to match the restored terminal
        const url = new URL(window.location.href);
        url.searchParams.set('terminal_id', lastTerminalId);
        window.history.replaceState({}, '', url);
    }
    
    // Don't clear the terminal active flag - we need it for buffer restoration
    
    // Initialize terminal with a slight delay to ensure DOM is ready
    setTimeout(() => {
        initTerminal();
    }, 100);
    
    // Save terminal buffer periodically
    setInterval(() => {
        if (window.location.pathname.includes('/terminal') && term) {
            saveTerminalBuffer();
        }
    }, 2000); // Save more frequently (every 2 seconds)
    
    // Make sure we have the terminal ID
    console.log('Terminal page loaded with terminal ID:', window.terminalId);
    
    // Override the event source handler
    if (typeof eventSource !== 'undefined') {
        console.log("Setting up event source handler");
        eventSource.onmessage = function(event) {
            if (!event.data) {
                return; // Skip keepalive
            }
            
            try {
                const data = JSON.parse(event.data);
                
                switch(data.type) {
                    case 'TranscriptionEvent':
                        const transcriptionElement = document.getElementById('transcription-text');
                        if (transcriptionElement) {
                            transcriptionElement.textContent = data.text;
                        }
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
                console.error('Error processing event:', e, event.data);
            }
        };
    } else {
        console.error("eventSource is not defined! Make sure core.js is loaded first.");
    }
});

// Add a debug function to check terminal state
function debugTerminal() {
    console.log("Terminal debug info:");
    console.log("- terminalReady:", terminalReady);
    console.log("- term initialized:", typeof term !== 'undefined');
    console.log("- fitAddon initialized:", typeof fitAddon !== 'undefined');
    console.log("- pendingData count:", pendingData.length);
    console.log("- terminal container:", document.getElementById('terminal-container'));
    
    if (typeof term !== 'undefined') {
        console.log("- term options:", term.options);
    }
}

// Call debug after a delay
setTimeout(debugTerminal, 2000);
