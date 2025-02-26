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

class Terminal:
    """Terminal emulator for web interface"""
    
    def __init__(self, name: str, session_id: str, columns: int = 80, main_lines: int = 10000, lines: int = 24):
        self.id = name
        self.name = name
        self.session_id = session_id
        self.columns = columns
        self.lines = lines
        
        # Setup screen buffer
        self.main_screen = pyte.Screen(columns, main_lines)
        self.alt_screen = pyte.Screen(columns, lines)
        self.main_stream = pyte.Stream(self.main_screen)
        self.alt_stream = pyte.Stream(self.alt_screen)
        self.current_screen = self.main_screen
        self.current_stream = self.main_stream
        
        # Create PTY
        self._master_fd, self._slave_fd = pty.openpty()
        self._set_winsize(self._slave_fd, lines, columns)
        
        # Start shell
        env = os.environ.copy()
        env['TERM'] = 'xterm'
        env['SHELL'] = '/bin/bash'
        
        # Use subprocess instead of fork/exec
        self._process = subprocess.Popen(
            ["/bin/bash", "--login"],
            stdin=self._slave_fd,
            stdout=self._slave_fd,
            stderr=self._slave_fd,
            env=env,
            start_new_session=True,
            preexec_fn=os.setsid
        )
        
        # Close slave fd in parent
        os.close(self._slave_fd)
        
        # Set master fd to non-blocking
        flags = fcntl.fcntl(self._master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Start reading thread
        self._run_thread = threading.Thread(target=self._run, daemon=True)
        self._run_thread.start()
        
        # Throttle screen updates
        self._last_update = 0
        self._update_interval = 0.1  # seconds
    
    def _set_winsize(self, fd, row, col, xpix=0, ypix=0):
        """Set terminal window size"""
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    
    def _run(self):
        """Background thread to read terminal output"""
        # Send a welcome message after a short delay
        time.sleep(0.5)
        self.send_input("echo 'Welcome to Alejandro Terminal'\n")
        
        buffer = b""
        
        while True:
            try:
                # Check if process is still alive
                if self._process.poll() is not None:
                    print(f"Terminal process exited with code {self._process.returncode}")
                    break
                
                # Wait for data with timeout
                rlist, _, _ = select.select([self._master_fd], [], [], 0.1)
                if self._master_fd in rlist:
                    try:
                        # Read available data
                        chunk = os.read(self._master_fd, 4096)
                        if not chunk:
                            break
                        
                        buffer += chunk
                        
                        # Process complete escape sequences
                        if buffer:
                            # Handle screen switching
                            if b'\x1b[?1049h' in buffer:
                                main_part, alt_part = buffer.split(b'\x1b[?1049h', 1)
                                self.main_stream.feed(main_part.decode('utf-8', errors='ignore'))
                                self.current_screen = self.alt_screen
                                self.current_stream = self.alt_stream
                                self.alt_stream.feed(alt_part.decode('utf-8', errors='ignore'))
                                buffer = b""
                            elif b'\x1b[?1049l' in buffer:
                                alt_part, main_part = buffer.split(b'\x1b[?1049l', 1)
                                self.alt_stream.feed(alt_part.decode('utf-8', errors='ignore'))
                                self.current_screen = self.main_screen
                                self.current_stream = self.main_stream
                                self.main_stream.feed(main_part.decode('utf-8', errors='ignore'))
                                buffer = b""
                            else:
                                # Feed data to current stream
                                self.current_stream.feed(buffer.decode('utf-8', errors='ignore'))
                                buffer = b""
                            
                            # Send screen update
                            self._send_screen_update()
                    except OSError as e:
                        if e.errno != 11:  # EAGAIN - Resource temporarily unavailable
                            raise
            except Exception as e:
                print(f"Terminal error: {e}")
                time.sleep(1)
    
    def _send_screen_update(self):
        """Send screen update event"""
        # Get raw text from screen
        raw_text = "\n".join("".join(row) for row in self.current_screen.display)
        
        # Clean up empty lines at the end for main screen
        if self.current_screen == self.main_screen:
            lines = raw_text.split('\n')
            empty_lines_count = 0
            for line in reversed(lines):
                if line.strip() == '':
                    empty_lines_count += 1
                else:
                    break
            
            if empty_lines_count > 0:
                lines = lines[:-empty_lines_count]
                raw_text = '\n'.join(lines)
        
        # Build color information
        color_info = {
            "cursor": {"x": self.current_screen.cursor.x, "y": self.current_screen.cursor.y},
            "colors": []
        }
        
        # Process each line in the buffer
        for y in range(len(self.current_screen.buffer)):
            row_colors = []
            for x in range(self.columns):
                if x in self.current_screen.buffer[y]:
                    char = self.current_screen.buffer[y][x]
                    color_data = {
                        "char": char.data,
                        "fg": char.fg,
                        "bg": char.bg,
                        "bold": char.bold,
                        "italics": char.italics,
                        "underscore": char.underscore,
                        "strikethrough": char.strikethrough,
                        "reverse": char.reverse,
                    }
                else:
                    color_data = {
                        "char": " ",
                        "fg": "default",
                        "bg": "default",
                        "bold": False,
                        "italics": False,
                        "underscore": False,
                        "strikethrough": False,
                        "reverse": False,
                    }
                row_colors.append(color_data)
            color_info["colors"].append(row_colors)
        
        # Send event
        push_event(TerminalScreenEvent(
            session_id=self.session_id,
            terminal_id=self.id,
            raw_text=raw_text,
            color_json=color_info,
            cursor_position={"x": self.current_screen.cursor.x, "y": self.current_screen.cursor.y}
        ))
    
    def send_input(self, data: str):
        """Send input to terminal"""
        try:
            os.write(self._master_fd, data.encode('utf-8'))
        except Exception as e:
            print(f"Error sending input to terminal: {e}")
    
    def close(self):
        """Close terminal"""
        try:
            # Kill process group
            if hasattr(self, '_process') and self._process.poll() is None:
                pgid = os.getpgid(self._process.pid)
                os.killpg(pgid, signal.SIGTERM)
                self._process.wait(timeout=1)
        except:
            pass
            
        try:
            os.close(self._master_fd)
        except:
            pass
