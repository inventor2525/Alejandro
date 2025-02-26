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

class DualScreenBuffer:
    """Manages both main and alternate screen buffers"""
    def __init__(self, columns, main_lines, alt_lines):
        self.main_screen = pyte.Screen(columns, main_lines)
        self.alt_screen = pyte.Screen(columns, alt_lines)
        self.main_stream = pyte.Stream(self.main_screen)
        self.alt_stream = pyte.Stream(self.alt_screen)
        self.current_screen = self.main_screen
        self.current_stream = self.main_stream

    def feed(self, data):
        """Feed data to the appropriate screen"""
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

    @property
    def display(self):
        return self.current_screen.display

    @property
    def cursor(self):
        return self.current_screen.cursor

    @property
    def buffer(self):
        return self.current_screen.buffer

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
        self._screen_buffer = DualScreenBuffer(columns, main_lines, lines)
        self._set_winsize(self._slave_fd, lines, columns)
        
        # Set master fd to non-blocking
        flags = fcntl.fcntl(self._master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Start shell
        env = os.environ.copy()
        env['TERM'] = 'xterm'
        env['SHELL'] = '/bin/bash'
        
        # Fork and exec
        pid = os.fork()
        if pid == 0:  # Child process
            try:
                os.close(self._master_fd)
                os.setsid()
                os.dup2(self._slave_fd, 0)
                os.dup2(self._slave_fd, 1)
                os.dup2(self._slave_fd, 2)
                os.close(self._slave_fd)
                os.execvpe("bash", ["bash", "--login"], env)
            except Exception as e:
                print(f"Child process error: {e}")
                os._exit(1)
        else:  # Parent process
            self._pid = pid
            os.close(self._slave_fd)
        
        # Start reading thread
        self._outputs = []
        self._output_lock = threading.Lock()
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
        
        while True:
            try:
                # Check if process is still alive
                try:
                    pid, status = os.waitpid(self._pid, os.WNOHANG)
                    if pid == self._pid:
                        print(f"Terminal process exited with status {status}")
                        break
                except:
                    pass
                
                # Wait for data with timeout
                rlist, _, _ = select.select([self._master_fd], [], [], 0.1)
                if self._master_fd in rlist:
                    try:
                        # Read available data
                        data = os.read(self._master_fd, 1024)
                        if not data:
                            break
                            
                        # Store output
                        with self._output_lock:
                            self._outputs.append(data)
                            
                        # Feed data to screen buffer
                        self._screen_buffer.feed(data)
                        
                        # Send screen update (throttled)
                        now = time.time()
                        if now - self._last_update > self._update_interval:
                            self._last_update = now
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
        raw_text = "\n".join("".join(row) for row in self._screen_buffer.display)
        
        # Clean up empty lines at the end for main screen
        if self._screen_buffer.current_screen == self._screen_buffer.main_screen:
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
            "cursor": {"x": self._screen_buffer.cursor.x, "y": self._screen_buffer.cursor.y},
            "colors": []
        }
        
        # Process each line in the buffer
        for y in range(len(self._screen_buffer.buffer)):
            row_colors = []
            for x in range(self.columns):
                if x in self._screen_buffer.buffer[y]:
                    char = self._screen_buffer.buffer[y][x]
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
        
        # Send event without logging the entire color data
        event = TerminalScreenEvent(
            session_id=self.session_id,
            terminal_id=self.id,
            raw_text=raw_text,
            color_json=color_info,
            cursor_position={"x": self._screen_buffer.cursor.x, "y": self._screen_buffer.cursor.y}
        )
        
        # Don't log the full event data
        from Alejandro.web.events import event_queue
        print(f"Sending terminal update for terminal: {self.id}")
        event_queue.put(event)
    
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
            try:
                pgid = os.getpgid(self._pid)
                os.killpg(pgid, signal.SIGTERM)
                # Wait briefly for process to terminate
                for _ in range(10):
                    try:
                        pid, _ = os.waitpid(self._pid, os.WNOHANG)
                        if pid == self._pid:
                            break
                    except:
                        break
                    time.sleep(0.1)
                else:
                    # Force kill if still running
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except:
                        pass
            except:
                pass
        except Exception as e:
            print(f"Error terminating terminal process: {e}")
            
        try:
            os.close(self._master_fd)
        except:
            pass
