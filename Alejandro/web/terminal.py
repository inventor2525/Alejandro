import os
import pty
import select
import struct
import termios
import threading
import time
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
        
        # Create PTY
        self._master_fd, self._slave_fd = pty.openpty()
        self._set_winsize(self._slave_fd, lines, columns)
        os.set_blocking(self._master_fd, True)
        
        # Setup screen buffer
        self.main_screen = pyte.Screen(columns, main_lines)
        self.alt_screen = pyte.Screen(columns, lines)
        self.main_stream = pyte.Stream(self.main_screen)
        self.alt_stream = pyte.Stream(self.alt_screen)
        self.current_screen = self.main_screen
        self.current_stream = self.main_stream
        
        # Start shell
        env = os.environ.copy()
        env['TERM'] = 'xterm'
        env['SHELL'] = '/bin/bash'
        
        pid = os.fork()
        if pid == 0:  # Child process
            os.close(self._master_fd)
            os.setsid()
            os.dup2(self._slave_fd, 0)
            os.dup2(self._slave_fd, 1)
            os.dup2(self._slave_fd, 2)
            os.close(self._slave_fd)
            os.execvpe("bash", ["bash", "--login"], env)
        else:  # Parent process
            os.close(self._slave_fd)
        
        # Start reading thread
        self._run_thread = threading.Thread(target=self._run, daemon=True)
        self._run_thread.start()
        
        # Throttle screen updates
        self._last_update = 0
        self._update_interval = 0.1  # seconds
    
    def _set_winsize(self, fd, row, col, xpix=0, ypix=0):
        """Set terminal window size"""
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        termios.ioctl(fd, termios.TIOCSWINSZ, winsize)
    
    def _run(self):
        """Background thread to read terminal output"""
        while True:
            try:
                rlist, _, _ = select.select([self._master_fd], [], [], 0.1)
                if self._master_fd in rlist:
                    data = os.read(self._master_fd, 1024)
                    if not data:
                        break
                    
                    # Handle screen switching
                    if b'\x1b[?1049h' in data:
                        main_part, alt_part = data.split(b'\x1b[?1049h', 1)
                        self.main_stream.feed(main_part.decode('utf-8', errors='ignore'))
                        self.current_screen = self.alt_screen
                        self.current_stream = self.alt_stream
                        self.alt_stream.feed(alt_part.decode('utf-8', errors='ignore'))
                    elif b'\x1b[?1049l' in data:
                        alt_part, main_part = data.split(b'\x1b[?1049l', 1)
                        self.alt_stream.feed(alt_part.decode('utf-8', errors='ignore'))
                        self.current_screen = self.main_screen
                        self.current_stream = self.main_stream
                        self.main_stream.feed(main_part.decode('utf-8', errors='ignore'))
                    else:
                        self.current_stream.feed(data.decode('utf-8', errors='ignore'))
                    
                    # Throttle screen updates
                    now = time.time()
                    if now - self._last_update > self._update_interval:
                        self._last_update = now
                        self._send_screen_update()
            except Exception as e:
                print(f"Terminal error: {e}")
                time.sleep(1)
    
    def _send_screen_update(self):
        """Send screen update event"""
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
            os.close(self._master_fd)
        except:
            pass
