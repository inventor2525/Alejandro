import os
import pty
import select
import subprocess
import threading
import fcntl
import struct
import termios
import time
import signal
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
		
		# Store screen contents for replay
		self.buffer = b""
		self.screen_buffer = ""
		self.last_output = ""
		
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
		
		# Wait briefly for the shell to initialize
		time.sleep(0.1)
		
		# Send a clear screen command to ensure a clean start
		# This should be handled properly by xterm.js
		self.clear()
	
	def _set_winsize(self, fd, row, col, xpix=0, ypix=0):
		"""Set terminal window size"""
		winsize = struct.pack("HHHH", row, col, xpix, ypix)
		fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
	
	def _read_loop(self):
		"""Read from PTY and send updates"""
		local_buffer = b""
		
		# Wait briefly for the shell to initialize
		time.sleep(0.1)
			
		while self.running:
			try:
				r, _, _ = select.select([self.master_fd], [], [], 0.1)
				if self.master_fd in r:
					data = os.read(self.master_fd, 1024)
					if data:
						local_buffer += data
						self.buffer += data
						
						# Accumulate data for a short time to reduce fragmentation
						# This helps prevent duplicate prompts caused by rapid partial updates
						time.sleep(0.01)
						
						# Check if there's more data available without blocking
						while True:
							r, _, _ = select.select([self.master_fd], [], [], 0)
							if self.master_fd not in r:
								break
							try:
								more_data = os.read(self.master_fd, 1024)
								if more_data:
									local_buffer += more_data
									self.buffer += more_data
								else:
									break
							except:
								break
								
						# Convert the data to text
						output_text = local_buffer.decode('utf-8', errors='replace')
						
						# Update screen buffer (trimming if needed)
						if len(self.buffer) > 102400:  # Keep roughly 100KB of history
							self.buffer = self.buffer[-51200:]  # Keep around 50KB
							
						# Decode buffer to text
						decoded_buffer = self.buffer.decode('utf-8', errors='replace')
						
						# Filter out any visible escape sequences
						import re
						# Replace visible escape sequences (appears as ^[[H^[[2J in terminal) with empty string
						self.screen_buffer = re.sub(r'\^\[\[H\^\[\[2J', '', decoded_buffer)
						
						# Also filter the current output
						output_text = re.sub(r'\^\[\[H\^\[\[2J', '', output_text)
						
						# Store last output for replay
						self.last_output = output_text
						
						# Send update with all accumulated data
						self._send_screen_update(output_text)
						local_buffer = b""
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
		
	def clear(self):
		"""Clear terminal screen"""
		self.send_input("\x1b[H\x1b[2J")  # ANSI escape sequence to clear screen
		
	def redraw(self):
		"""Redraw the terminal screen (Ctrl-L)"""
		self.send_input("\x0c")  # Ctrl-L to redraw screen
		
	def replay_buffer(self):
		"""Send the complete buffer to the client for display"""
		if not self.screen_buffer:
			return
			
		# Use a proper terminal sequence to clear the screen
		clear_event = TerminalScreenEvent(
			session_id=self.session_id,
			terminal_id=self.name,
			raw_text='\x1b[2J\x1b[H'  # ANSI clear screen and move cursor to home
		)
		push_event(clear_event)
		
		# Add a small delay to ensure the clear command is processed
		time.sleep(0.05)
		
		# Filter out any raw escape sequences that might be visible
		# This regex matches the common clear screen sequence that appears as text 
		import re
		clean_buffer = re.sub(r'\^\[\[H\^\[\[2J', '', self.screen_buffer)
			
		# Then send the cleaned buffer
		event = TerminalScreenEvent(
			session_id=self.session_id,
			terminal_id=self.name,
			raw_text=clean_buffer
		)
		push_event(event)
	
	def close(self):
		"""Close terminal"""
		self.running = False
		try:
			# Try to terminate process gracefully first
			self.process.terminate()
			
			# Give it a moment to terminate
			for _ in range(5):
				if self.process.poll() is not None:
					break
				time.sleep(0.1)
				
			# Force kill if still running
			if self.process.poll() is None:
				pgid = os.getpgid(self.process.pid)
				os.killpg(pgid, signal.SIGKILL)
				
			# Close file descriptors
			os.close(self.master_fd)
			os.close(self.slave_fd)
		except Exception as e:
			print(f"Error closing terminal: {e}")
