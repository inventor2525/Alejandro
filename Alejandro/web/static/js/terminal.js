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
    } else if (e.key === 'Home') {
        data = '\x1b[H';
    } else if (e.key === 'End') {
        data = '\x1b[F';
    } else if (e.key === 'Delete') {
        data = '\x1b[3~';
    } else if (e.key === 'PageUp') {
        data = '\x1b[5~';
    } else if (e.key === 'PageDown') {
        data = '\x1b[6~';
    } else if (e.ctrlKey && e.key.length === 1) {
        // Control characters
        const code = e.key.charCodeAt(0) - 64;
        if (code > 0 && code < 27) {
            data = String.fromCharCode(code);
        }
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
    })
    .then(response => response.json())
    .then(data => {
        console.log('Terminal input response:', data);
    })
    .catch(error => {
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
        
        if (y < colors.length) {
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
eventSource.onmessage = function(event) {
    if (!event.data) {
        console.log('Skipping keepalive');
        return;
    }
    
    console.log('Raw SSE event:', event);
    console.log('Event data:', event.data);
    
    const data = JSON.parse(event.data);
    console.log('Parsed event data:', data);
    
    switch(data.type) {
        case 'TranscriptionEvent':
            document.getElementById('transcription-text').textContent = data.text;
            break;
        case 'NavigationEvent':
            console.log('Navigating to:', data.screen);
            if (data.force || window.location.pathname.substring(1) !== data.screen) {
                window.location.href = '/' + data.screen + '?session=' + data.session_id;
            }
            break;
        case 'TerminalScreenEvent':
            renderTerminal(data);
            break;
    }
};

// Focus terminal on load
window.addEventListener('load', function() {
    terminal.focus();
});
