function openOrFocus(url, targetName) {
    let win = window.open('', targetName);
    if (win === null) {
        win = window.open(url, targetName);
    }
    else {
        try {
            if (win.location.href === 'about:blank') {
                win.close();
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