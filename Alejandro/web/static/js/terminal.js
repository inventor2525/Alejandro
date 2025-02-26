// Terminal handling
const terminal = document.getElementById('terminal-container');
const display = document.getElementById('terminal-display');
const cursor = document.getElementById('terminal-cursor');

// Keep focus on terminal
terminal.addEventListener('click', function() {
    terminal.focus();
});

// Handle key input
terminal.addEventListener('keydown', function(e) {
    e.preventDefault(); // Prevent default browser actions
    
    let data = '';
    if (e.key === 'Enter') {
        data = '\r';
    } else if (e.key === 'Backspace') {
        data = '\b';
    } else if (e.key === 'Tab') {
        data = '\t';
    } else if (e.key === 'Escape') {
        data = '\x1b';
    } else if (e.key === 'ArrowUp') {
        data = '\x1b[A';
    } else if (e.key === 'ArrowDown') {
        data = '\x1b[B';
    } else if (e.key === 'ArrowRight') {
        data = '\x1b[C';
    } else if (e.key === 'ArrowLeft') {
        data = '\x1b[D';
    } else if (e.key.length === 1) {
        // Regular character
        data = e.key;
    } else {
        return; // Ignore other special keys
    }
    
    // Send input to server
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
    }).catch(error => {
        console.error('Error sending terminal input:', error);
    });
});

// Keep focus on terminal
terminal.addEventListener('blur', function() {
    terminal.focus();
});

// Handle terminal screen updates
function renderTerminal(data) {
    if (data.terminal_id !== window.terminalId) {
        return; // Skip updates for other terminals
    }
    
    display.innerHTML = '';
    
    const lines = data.raw_text.split('\n');
    const colors = data.color_json.colors;
    
    lines.forEach((line, y) => {
        const lineDiv = document.createElement('div');
        lineDiv.className = 'terminal-line';
        
        if (colors[y]) {
            colors[y].forEach((char, x) => {
                const span = document.createElement('span');
                span.textContent = char.char || ' ';
                
                let style = '';
                if (char.fg && char.fg !== 'default') style += `color: ${char.fg};`;
                if (char.bg && char.bg !== 'default') style += `background-color: ${char.bg};`;
                if (char.bold) style += 'font-weight: bold;';
                if (char.italics) style += 'font-style: italic;';
                if (char.underscore) style += 'text-decoration: underline;';
                if (char.strikethrough) style += 'text-decoration: line-through;';
                if (char.reverse) {
                    // Swap foreground and background
                    const tempFg = char.fg;
                    const tempBg = char.bg;
                    if (tempBg && tempBg !== 'default') style += `color: ${tempBg};`;
                    if (tempFg && tempFg !== 'default') style += `background-color: ${tempFg};`;
                }
                
                span.style = style;
                lineDiv.appendChild(span);
            });
        } else {
            lineDiv.textContent = line;
        }
        
        display.appendChild(lineDiv);
    });
    
    // Position cursor
    cursor.style.top = `${data.cursor_position.y * 1.2}em`;
    cursor.style.left = `${data.cursor_position.x * 0.6}em`;
    
    // Scroll to bottom if we're near the bottom already
    const isNearBottom = display.scrollTop + display.clientHeight >= display.scrollHeight - 50;
    if (isNearBottom) {
        display.scrollTop = display.scrollHeight;
    }
}

// Extend the existing event source handler
const originalOnMessage = eventSource.onmessage;
eventSource.onmessage = function(event) {
    if (!event.data) return;
    
    const data = JSON.parse(event.data);
    
    if (data.type === 'TerminalScreenEvent') {
        renderTerminal(data);
    } else if (originalOnMessage) {
        // Call the original handler for other event types
        originalOnMessage(event);
    }
};

// Focus terminal on load
window.addEventListener('load', function() {
    terminal.focus();
});
