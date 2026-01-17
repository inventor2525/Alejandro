import os
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control, ModalControl
from Alejandro.Core.Control import Control

bp = Blueprint('braindump', __name__)

# Directory for storing notes
NOTES_DIR = Path.home() / "Documents" / "Alejandro" / "Notes"

def ensure_git_repo():
	"""Ensure notes directory exists and is a git repository"""
	NOTES_DIR.mkdir(parents=True, exist_ok=True)
	git_dir = NOTES_DIR / ".git"

	if not git_dir.exists():
		print(f"[BRAIN DUMP] Initializing git repository at {NOTES_DIR}")
		subprocess.run(["git", "init"], cwd=NOTES_DIR, check=True)
		subprocess.run(["git", "config", "user.name", "Alejandro Brain Dump"], cwd=NOTES_DIR, check=True)
		subprocess.run(["git", "config", "user.email", "braindump@alejandro.local"], cwd=NOTES_DIR, check=True)

# Initialize on module load
ensure_git_repo()

def git_commit(message: str):
	"""Commit all changes with given message"""
	try:
		subprocess.run(["git", "add", "-A"], cwd=NOTES_DIR, check=False)
		subprocess.run(["git", "commit", "-m", message], cwd=NOTES_DIR, check=False)
		print(f"[BRAIN DUMP GIT] {message}")
	except Exception as e:
		print(f"[BRAIN DUMP GIT ERROR] {e}")

class MarkdownNote:
	"""Helper class to parse and manage markdown note structure"""

	def __init__(self, filepath: Path):
		self.filepath = filepath
		self.content = ""
		self.change_log = []

		if filepath.exists():
			self._parse()

	def _parse(self):
		"""Parse existing markdown file"""
		with open(self.filepath, 'r') as f:
			text = f.read()

		# Split by main headers
		if "# Note Content" in text:
			parts = text.split("# Note Content", 1)
			if len(parts) > 1:
				rest = parts[1]

				# Check for change log
				if "# Change Log" in rest:
					content_part, log_part = rest.split("# Change Log", 1)
					self.content = content_part.strip()

					# Parse CSV change log
					log_lines = log_part.strip().split('\n')
					for line in log_lines:
						line = line.strip()
						if line and ',' in line and not line.startswith('start_time'):
							parts = line.split(',', 2)
							if len(parts) >= 3:
								self.change_log.append({
									'start': parts[0],
									'end': parts[1],
									'action': parts[2]
								})
				else:
					self.content = rest.strip()
		else:
			# Legacy or malformed - just grab everything
			self.content = text.strip()

	def append_content(self, text: str):
		"""Append text to note content with paragraph separation"""
		if self.content:
			self.content += "\n\n" + text
		else:
			self.content = text

	def add_header(self, header_text: str):
		"""Add a ## level header"""
		header = f"## {header_text}"
		if self.content:
			self.content += "\n\n" + header + "\n\n"
		else:
			self.content = header + "\n\n"

	def add_change_log_entry(self, start_time: datetime, end_time: datetime, action: str):
		"""Add entry to change log"""
		self.change_log.append({
			'start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
			'end': end_time.strftime('%Y-%m-%d %H:%M:%S'),
			'action': action
		})

	def save(self):
		"""Write markdown file with proper structure"""
		output = "# Note Content\n\n"
		output += self.content
		output += "\n\n# Change Log\n\n"
		output += "start_time,end_time,action\n"
		for entry in self.change_log:
			output += f"{entry['start']},{entry['end']},{entry['action']}\n"

		self.filepath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.filepath, 'w') as f:
			f.write(output)

@screen_type
class BrainDumpScreen(Screen):
	"""Simple offline voice-to-file note-taking screen with git tracking and markdown structure"""

	def __init__(self, session: 'Session'):
		super().__init__(
			session=session,
			title="Brain Dump",
			controls=[
				session.make_back_control()
			])

		# State management
		self.current_filename: str = ""
		self.current_subdir: str = ""  # Relative to NOTES_DIR
		self.content_buffer: str = ""
		self.dictation_start_time: datetime = None
		self.dictation_end_time: datetime = None

	def _get_current_dir(self) -> Path:
		"""Get absolute path of current working directory"""
		if self.current_subdir:
			return NOTES_DIR / self.current_subdir
		return NOTES_DIR

	def _get_filepath(self, filename: str) -> Path:
		"""Get absolute filepath in current directory"""
		# Ensure .md extension
		if not filename.endswith('.md'):
			filename = filename + '.md'

		# Replace spaces with underscores
		filename = filename.replace(' ', '_')

		return self._get_current_dir() / filename

	@control(
		keyphrases=["change directory", "set directory", "go to directory"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def change_directory(self, control: ModalControl):
		"""Change current subdirectory - use 'slash' to separate path components"""
		dir_path = control.collected_words.strip()
		if not dir_path:
			print("[BRAIN DUMP] No directory path provided")
			return

		# Replace spoken "slash" with actual slash
		dir_path = dir_path.replace(' slash ', '/')
		dir_path = dir_path.replace('slash ', '/')
		dir_path = dir_path.replace(' slash', '/')

		# Remove leading/trailing slashes
		dir_path = dir_path.strip('/')

		# Validate it's safe (no parent directory traversal)
		if '..' in dir_path:
			print("[BRAIN DUMP] Invalid directory path - no parent directory traversal allowed")
			return

		# Create if doesn't exist
		new_dir = NOTES_DIR / dir_path
		new_dir.mkdir(parents=True, exist_ok=True)

		self.current_subdir = dir_path
		print(f"[BRAIN DUMP] Changed to directory: {dir_path or 'root'}")
		git_commit(f"created directory '{dir_path}'")

	@control(keyphrases=["root directory", "go to root", "reset directory"])
	def root_directory(self, control: Control):
		"""Return to root notes directory"""
		self.current_subdir = ""
		print("[BRAIN DUMP] Changed to root directory")

	@control(
		keyphrases=["new note", "create file", "new file"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def new_note(self, control: ModalControl):
		"""Set filename for new note (always .md)"""
		filename = control.collected_words.strip()
		if not filename:
			print("[BRAIN DUMP] No filename provided")
			return

		# Replace spaces with underscores
		filename = filename.replace(' ', '_')

		# Ensure .md extension
		if not filename.endswith('.md'):
			filename = filename + '.md'

		self.current_filename = filename
		self.content_buffer = ""
		print(f"[BRAIN DUMP] New note: {filename} in {self.current_subdir or 'root'}")

	@control(
		keyphrases=["begin dictation", "start dictating", "start writing"],
		deactivate_phrases=["end dictation", "stop dictating", "finished dictating", "done"]
	)
	def dictate_content(self, control: ModalControl):
		"""Accumulate note content - each cycle creates a new paragraph"""
		# Record timing
		if not self.dictation_start_time:
			self.dictation_start_time = datetime.now()

		self.dictation_end_time = datetime.now()

		dictated_text = control.collected_words.strip()
		if dictated_text:
			# Each dictation cycle creates a new paragraph
			if self.content_buffer:
				self.content_buffer += "\n\n" + dictated_text
			else:
				self.content_buffer = dictated_text
			print(f"[BRAIN DUMP] Buffer ({len(self.content_buffer)} chars)")

	@control(
		keyphrases=["add header", "create header", "new header"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def add_header(self, control: ModalControl):
		"""Add a ## level header to the buffer"""
		header_text = control.collected_words.strip()
		if not header_text:
			print("[BRAIN DUMP] No header text provided")
			return

		header = f"## {header_text}"
		if self.content_buffer:
			self.content_buffer += "\n\n" + header + "\n\n"
		else:
			self.content_buffer = header + "\n\n"

		print(f"[BRAIN DUMP] Added header: {header_text}")

	@control(keyphrases=["save", "save note", "save file"])
	def save_note(self, control: Control):
		"""Save current buffer to file with markdown structure"""
		if not self.current_filename:
			print("[BRAIN DUMP] No filename set. Say 'new note' first.")
			return

		if not self.content_buffer.strip():
			print("[BRAIN DUMP] Nothing to save - buffer is empty")
			return

		filepath = self._get_filepath(self.current_filename)

		# Load or create note
		note = MarkdownNote(filepath)

		# Determine if creating or modifying
		is_new = not filepath.exists()
		action = "created" if is_new else "modified"

		# Append buffer content
		note.append_content(self.content_buffer)

		# Add change log entry with dictation timing
		if self.dictation_start_time and self.dictation_end_time:
			note.add_change_log_entry(
				self.dictation_start_time,
				self.dictation_end_time,
				action
			)

		# Save
		note.save()

		print(f"[BRAIN DUMP] Saved {len(self.content_buffer)} chars to {filepath}")

		# Git commit
		git_commit(f"{action} note '{self.current_filename}'")

		# Clear buffer and timing
		self.content_buffer = ""
		self.dictation_start_time = None
		self.dictation_end_time = None

	@control(
		keyphrases=["append to file", "add to note", "append to note"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def append_to_file(self, control: ModalControl):
		"""Append to an existing file"""
		filename = control.collected_words.strip()
		if not filename:
			print("[BRAIN DUMP] No filename provided")
			return

		filename = filename.replace(' ', '_')
		if not filename.endswith('.md'):
			filename = filename + '.md'

		filepath = self._get_filepath(filename)

		if not filepath.exists():
			print(f"[BRAIN DUMP] File not found: {filename}")
			return

		# Load existing note
		note = MarkdownNote(filepath)

		self.current_filename = filename
		self.content_buffer = note.content
		print(f"[BRAIN DUMP] Loaded {filename} ({len(note.content)} chars). Begin dictating to append.")

	@control(keyphrases=["list notes", "show notes", "list files"])
	def list_notes(self, control: Control):
		"""List all saved notes in current directory"""
		current_dir = self._get_current_dir()
		notes = sorted([f.name for f in current_dir.iterdir() if f.is_file() and f.suffix == '.md'])

		if not notes:
			print(f"[BRAIN DUMP] No notes in {self.current_subdir or 'root'}")
			return

		print(f"\n[BRAIN DUMP] Notes in {self.current_subdir or 'root'}:")
		for note in notes:
			filepath = current_dir / note
			size = filepath.stat().st_size
			print(f"  - {note} ({size} bytes)")
		print()

	@control(keyphrases=["list directories", "show directories", "list subdirectories"])
	def list_directories(self, control: Control):
		"""List subdirectories in current directory"""
		current_dir = self._get_current_dir()
		subdirs = sorted([d.name for d in current_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

		if not subdirs:
			print(f"[BRAIN DUMP] No subdirectories in {self.current_subdir or 'root'}")
			return

		print(f"\n[BRAIN DUMP] Subdirectories in {self.current_subdir or 'root'}:")
		for subdir in subdirs:
			print(f"  - {subdir}/")
		print()

	@control(
		keyphrases=["read note", "open note", "show note"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def read_note(self, control: ModalControl):
		"""Read/display a note's contents"""
		filename = control.collected_words.strip()
		if not filename:
			print("[BRAIN DUMP] No filename provided")
			return

		filename = filename.replace(' ', '_')
		if not filename.endswith('.md'):
			filename = filename + '.md'

		filepath = self._get_filepath(filename)

		if not filepath.exists():
			print(f"[BRAIN DUMP] File not found: {filename}")
			return

		try:
			with open(filepath, 'r') as f:
				content = f.read()

			print(f"\n[BRAIN DUMP] === {filename} ===")
			print(content)
			print(f"=== End of {filename} ===\n")

		except Exception as e:
			print(f"[BRAIN DUMP ERROR] Failed to read: {e}")

	@control(
		keyphrases=["delete note", "remove note", "delete file"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def delete_note(self, control: ModalControl):
		"""Delete a note file"""
		filename = control.collected_words.strip()
		if not filename:
			print("[BRAIN DUMP] No filename provided")
			return

		filename = filename.replace(' ', '_')
		if not filename.endswith('.md'):
			filename = filename + '.md'

		filepath = self._get_filepath(filename)

		if not filepath.exists():
			print(f"[BRAIN DUMP] File not found: {filename}")
			return

		try:
			filepath.unlink()
			print(f"[BRAIN DUMP] Deleted {filename}")

			# Git commit
			git_commit(f"deleted note '{filename}'")

			# Clear state if we deleted the current file
			if self.current_filename == filename:
				self.current_filename = ""
				self.content_buffer = ""

		except Exception as e:
			print(f"[BRAIN DUMP ERROR] Failed to delete: {e}")

	@control(
		keyphrases=["delete directory", "remove directory"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def delete_directory(self, control: ModalControl):
		"""Delete a subdirectory (must be empty)"""
		dir_path = control.collected_words.strip()
		if not dir_path:
			print("[BRAIN DUMP] No directory path provided")
			return

		# Replace spoken "slash" with actual slash
		dir_path = dir_path.replace(' slash ', '/')
		dir_path = dir_path.replace('slash ', '/')
		dir_path = dir_path.replace(' slash', '/')
		dir_path = dir_path.strip('/')

		if '..' in dir_path:
			print("[BRAIN DUMP] Invalid directory path")
			return

		target_dir = NOTES_DIR / dir_path

		if not target_dir.exists():
			print(f"[BRAIN DUMP] Directory not found: {dir_path}")
			return

		if not target_dir.is_dir():
			print(f"[BRAIN DUMP] Not a directory: {dir_path}")
			return

		try:
			target_dir.rmdir()  # Only removes if empty
			print(f"[BRAIN DUMP] Deleted directory: {dir_path}")
			git_commit(f"deleted directory '{dir_path}'")

			# If we were in the deleted directory, go to parent
			if self.current_subdir.startswith(dir_path):
				self.current_subdir = str(Path(dir_path).parent) if Path(dir_path).parent != Path('.') else ""
				print(f"[BRAIN DUMP] Moved to: {self.current_subdir or 'root'}")

		except OSError as e:
			print(f"[BRAIN DUMP ERROR] Failed to delete directory (may not be empty): {e}")

	@control(keyphrases=["clear buffer", "clear", "reset buffer", "start over"])
	def clear_buffer(self, control: Control):
		"""Clear the content buffer without saving"""
		self.content_buffer = ""
		self.dictation_start_time = None
		self.dictation_end_time = None
		print("[BRAIN DUMP] Buffer cleared")

	@control(keyphrases=["new session", "reset", "clear all"])
	def reset_session(self, control: Control):
		"""Reset filename and buffer"""
		self.current_filename = ""
		self.content_buffer = ""
		self.dictation_start_time = None
		self.dictation_end_time = None
		print("[BRAIN DUMP] Session reset")

	@control(keyphrases=["status", "current file", "what file", "where am i"])
	def show_status(self, control: Control):
		"""Show current directory, filename and buffer status"""
		print(f"[BRAIN DUMP] Current directory: {self.current_subdir or 'root'}")

		if self.current_filename:
			print(f"[BRAIN DUMP] Current file: {self.current_filename}")
		else:
			print("[BRAIN DUMP] No file set")

		if self.content_buffer:
			print(f"[BRAIN DUMP] Buffer: {len(self.content_buffer)} chars")
		else:
			print("[BRAIN DUMP] Buffer is empty")

@bp.route(f'/{BrainDumpScreen.url()}')
def show_screen() -> str:
	"""Generic screen route handler"""
	session_id = request.args.get('session')

	session = get_or_create_session(session_id)
	screen = session.current_or_get(BrainDumpScreen)
	return render_template(
		'base.html',
		screen=screen,
		session_id=session.id,
		**screen.get_template_data()
	)
