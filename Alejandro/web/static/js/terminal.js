// Initialize xterm.js
let term;
let fitAddon;
let serializeAddon;
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
        
        if (window.SerializeAddon) {
            serializeAddon = new window.SerializeAddon.SerializeAddon();
            term.loadAddon(serializeAddon);
            console.log("Serialize addon loaded");
        } else {
            console.warn("SerializeAddon not available");
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

    if (savedBuffer && serializeAddon) {
        try {
            console.log(`Restoring terminal buffer for ${window.terminalId} using serialize addon`);
            
            // Clear terminal first
            term.clear();
            
            // Write the serialized buffer directly
            term.write(savedBuffer);
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
    if (!term || !serializeAddon) return;
    
    try {
        // Use the serialize addon to get the terminal state
        const serializedState = serializeAddon.serialize();
        
        // Store the serialized state
        localStorage.setItem(`terminal_buffer_${window.terminalId}`, serializedState);
        console.log(`Manually saved terminal buffer for ${window.terminalId} using serialize addon`);
    } catch (e) {
        console.error("Error saving terminal buffer:", e);
    }
}

// Terminal switch is now handled through the TerminalScreen controls
// No need for custom terminal switching UI

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
    
    // Write new content directly to terminal
    term.write(data.raw_text);
}

// Store terminal state when navigating away
window.addEventListener('beforeunload', function(event) {
    // Only store state if we're on the terminal page
    if (window.location.pathname.includes('/terminal')) {
        console.log("Storing terminal state before navigation");
        localStorage.setItem('terminalActive', 'true');
        localStorage.setItem('lastTerminalId', window.terminalId);
        
        // Save the terminal buffer using serialize addon
        if (term && serializeAddon) {
            try {
                const serializedState = serializeAddon.serialize();
                localStorage.setItem(`terminal_buffer_${window.terminalId}`, serializedState);
                console.log(`Stored terminal buffer for ${window.terminalId} using serialize addon`);
            } catch (e) {
                console.error("Error saving terminal buffer:", e);
            }
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
        if (term && serializeAddon) {
            try {
                const serializedState = serializeAddon.serialize();
                localStorage.setItem(`terminal_buffer_${window.terminalId}`, serializedState);
                console.log(`Stored terminal buffer for ${window.terminalId} using serialize addon`);
            } catch (e) {
                console.error("Error saving terminal buffer:", e);
            }
        }
    }
});

// Custom event handler for terminal events
function handleTerminalEvents(event) {
    if (!event.data) {
        return; // Skip keepalive
    }
    
    try {
        const data = JSON.parse(event.data);
        console.log('Received event type:', data.type);
        
        if (data.type === 'TerminalScreenEvent') {
            console.log('Terminal event received for:', data.terminal_id);
            
            // Check if we need to switch terminals
            if (data.terminal_id !== window.terminalId) {
                // Save current terminal buffer before switching
                if (term && serializeAddon) {
                    try {
                        const serializedState = serializeAddon.serialize();
                        localStorage.setItem(`terminal_buffer_${window.terminalId}`, serializedState);
                        console.log(`Saved buffer for terminal ${window.terminalId} before switching`);
                    } catch (e) {
                        console.error("Error saving terminal buffer:", e);
                    }
                }
                
                // Update terminal ID
                window.terminalId = data.terminal_id;
                console.log('Switching to terminal:', window.terminalId);
                
                // Update URL without reloading
                const url = new URL(window.location.href);
                url.searchParams.set('terminal_id', window.terminalId);
                window.history.replaceState({}, '', url);
                
                // Update page title
                document.title = `Terminal - ${window.terminalId} - Alejandro`;
                // Update h1 title if it exists
                const titleElement = document.querySelector('h1');
                if (titleElement) {
                    titleElement.textContent = `Terminal - ${window.terminalId}`;
                }
                
                // Clear terminal
                if (term) {
                    term.clear();
                }
                
                // Restore buffer for this terminal if available
                const savedBuffer = localStorage.getItem(`terminal_buffer_${window.terminalId}`);
                if (savedBuffer && serializeAddon && term) {
                    try {
                        term.write(savedBuffer);
                        console.log(`Restored buffer for terminal ${window.terminalId}`);
                    } catch (e) {
                        console.error("Error restoring terminal buffer:", e);
                    }
                }
            }
            
            // Process the terminal data if there is any
            if (data.raw_text) {
                handleTerminalData(data);
            }
        }
    } catch (e) {
        console.error('Error processing terminal event:', e, event.data);
    }
}

// Initialize and set up event handling
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
    
    // Initialize terminal
    initTerminal();
    
    // Save terminal buffer periodically
    setInterval(() => {
        if (window.location.pathname.includes('/terminal') && term) {
            saveTerminalBuffer();
        }
    }, 5000); // Save every 5 seconds
    
    // Make sure we have the terminal ID
    console.log('Terminal page loaded with terminal ID:', window.terminalId);
    
    // Set up event handling
    if (typeof eventSource !== 'undefined') {
        console.log("Setting up terminal event listener");
        
        // Remove any existing event listener
        eventSource.removeEventListener('message', handleTerminalEvents);
        
        // Add our terminal event listener
        eventSource.addEventListener('message', handleTerminalEvents);
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
