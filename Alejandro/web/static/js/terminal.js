// Initialize xterm.js
let term;
let fitAddon;
let serializeAddon;
let terminalReady = false;
let pendingData = [];

// We're not going to adjust terminal size in JS anymore

// Initialize terminal
function initTerminal() {
    console.log("Initializing xterm.js terminal");
    
    // If terminal is already initialized, just return
    if (terminalReady && term) {
        console.log("Terminal already initialized, skipping initialization");
        return;
    }
    
    // No size adjustment in JS
    
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
        scrollback: 10000,  // Significantly increased scrollback
        allowTransparency: false,
        convertEol: true,   // Convert line feed characters to carriage return + line feed
        disableStdin: false, // Ensure input is enabled
        rows: 30            // Set a specific number of rows to ensure height calculation is correct
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
            // Delay the fit operation slightly to ensure the container is fully rendered
            setTimeout(() => {
                fitAddon.fit();
                console.log("Terminal fitted to container");
                
                // After fitting, send the new dimensions to the server
                const dims = term.options;
                sendTerminalResize(dims.cols, dims.rows);
            }, 50);
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
        if (fitAddon && term) {
            // Debounce resize to prevent too many events
            clearTimeout(window.resizeTimer);
            window.resizeTimer = setTimeout(() => {
                console.log("Window resized, fitting terminal");
                
                // No size adjustment in JS
                
                // Then fit the terminal to its container
                fitAddon.fit();
                
                // Send terminal size to server
                const dimensions = term.options;
                sendTerminalResize(dimensions.cols, dimensions.rows);
                
                // Focus the terminal after resize
                term.focus();
            }, 100);
        }
    });

    // Mark terminal as ready
    terminalReady = true;
    console.log("Terminal ready");
    
    // Add scrollToBottom method if it doesn't exist
    if (!term.scrollToBottom) {
        term.scrollToBottom = function() {
            if (term._core && term._core.viewport) {
                term._core.viewport.scrollBarWidth = 15; // Make sure scrollbar is visible
                term._core.viewport.syncScrollArea();
                term._core.viewport.element.scrollTop = term._core.viewport.element.scrollHeight;
                console.log("Manually scrolled terminal to bottom");
            }
        };
    }

    // We will not restore buffer here on initial load
// This will be handled by the server sending initial state
// Process any pending data
if (pendingData.length > 0) {
    console.log(`Processing ${pendingData.length} pending data items`);
    pendingData.forEach(data => {
        term.write(data);
    });
    pendingData = [];
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
    fetch(`/terminal/input`, {
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
    fetch(`/terminal/resize`, {
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

// We no longer manually save terminal buffers
// Terminal state is managed by the server

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
    // Make sure we're getting proper data
    if (data.raw_text && data.raw_text.length > 0) {
        console.log(`Writing ${data.raw_text.length} chars to terminal`);
        // The terminal handles ANSI escape sequences properly
        term.write(data.raw_text);
        
        // Scroll to bottom after writing content
        setTimeout(() => {
            // Try to scroll to bottom to ensure we see the prompt
            if (term && term._core) {
                term.scrollToBottom();
            }
        }, 10);
    }
}

// Store terminal session info when navigating away
window.addEventListener('beforeunload', function(event) {
    // Only store information if we're on the terminal page
    if (window.location.pathname.includes('/terminal')) {
        console.log("Storing terminal session info before navigation");
        localStorage.setItem('terminalActive', 'true');
        localStorage.setItem('lastTerminalId', window.terminalId);
        // We no longer save terminal buffer, as it will be managed by the server
    }
});

// We don't need to save terminal state on navigation clicks anymore
// State is managed on the server side

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
                // We no longer save terminal buffers before switching
                // Terminal state is managed by the server
                
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
                
                // Clear the terminal - we'll get a full buffer from the server
                if (term) {
                    console.log(`Clearing terminal for switch to: ${window.terminalId}`);
                    term.clear();
                }
                
                console.log(`Switching to terminal: ${window.terminalId}`);
                
                // The server will send the complete buffer
                // No need to request anything else
                term.focus();
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
    
    // We no longer periodically save terminal buffers
    // Terminal state is managed by the server
    
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
