import os
import pty
import select
import struct
import termios
import fcntl
import threading
import time
import signal
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional

import pyte
from Alejandro.web.events import TerminalScreenEvent, push_event

import os
import pty
import select
import subprocess
import threading
import fcntl
import struct
import termios
import time
from typing import Dict, Any, Optional
from Alejandro.web.events import TerminalScreenEvent, push_event

class Terminal:
    """Terminal emulator for web interface"""
    
    def __init__(self, name: str, session_id: str, columns: int = 80, lines: int = 24):
        self.name = name
        self.session_id = session_id
        self.columns = columns
        self.lines = lines
        self.running = True
        
        # Create PTY
        self.master_fd, self.slave_fd = pty.openpty()
        
        # Set non-blocking mode for master
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Set terminal size
        self._set_winsize(self.slave_fd, self.lines, self.columns)
        
        # Start shell
        self.process = subprocess.Popen(
            [os.environ.get('SHELL', '/bin/bash')],
            preexec_fn=os.setsid,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            universal_newlines=True
        )
        
        # Start read thread
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        # Send initial screen update
        self._send_screen_update()
    
    def _set_winsize(self, fd, row, col, xpix=0, ypix=0):
        """Set terminal window size"""
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    
    def _read_loop(self):
        """Read from PTY and send updates"""
        buffer = b""
        
        # Skip initial output which often contains empty lines
        try:
            # Wait briefly for initial output
            time.sleep(0.1)
            # Read and discard initial output
            while True:
                r, _, _ = select.select([self.master_fd], [], [], 0.01)
                if not (self.master_fd in r):
                    break
                os.read(self.master_fd, 1024)
        except:
            pass
            
        while self.running:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if self.master_fd in r:
                    data = os.read(self.master_fd, 1024)
                    if data:
                        buffer += data
                        # Send update immediately to ensure responsiveness
                        self._send_screen_update(buffer.decode('utf-8', errors='replace'))
                        buffer = b""
            except (OSError, IOError) as e:
                if e.errno != 11:  # EAGAIN
                    print(f"Terminal read error: {e}")
                    break
            except Exception as e:
                print(f"Terminal error: {e}")
                break
    
    def _send_screen_update(self, raw_text: str = ""):
        """Send terminal screen update to client"""
        event = TerminalScreenEvent(
            session_id=self.session_id,
            terminal_id=self.name,
            raw_text=raw_text
        )
        push_event(event)
    
    def send_input(self, data: str):
        """Send input to terminal"""
        try:
            os.write(self.master_fd, data.encode('utf-8'))
        except Exception as e:
            print(f"Error sending input to terminal: {e}")
    
    def resize(self, columns: int, lines: int):
        """Resize terminal"""
        self.columns = columns
        self.lines = lines
        self._set_winsize(self.slave_fd, lines, columns)
    
    def close(self):
        """Close terminal"""
        self.running = False
        try:
            self.process.terminate()
            os.close(self.master_fd)
            os.close(self.slave_fd)
        except Exception as e:
            print(f"Error closing terminal: {e}")
