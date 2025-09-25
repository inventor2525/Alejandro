function debugOnServer(msg) {
    fetch(`/debugOnServer`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: localStorage.getItem('sessionId'),
            msg:msg
        })
    })
    .then(response => response.json())
}

function openOrFocus(url, targetName) {
    let win = window.open('', targetName);
    if (win === null) {
        win = window.open(url, targetName);
    }
    else {
        try {
            if (win.location.href === 'about:blank') {
                // win.close();
                win = window.open(url, targetName);
            }
            else {
                win.focus();
            }
        }
        catch (e) {
            win.focus();
        }
    }
    return win;
}