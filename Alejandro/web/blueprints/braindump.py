import os
from pathlib import Path
from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control, ModalControl
from Alejandro.Core.Control import Control

bp = Blueprint('braindump', __name__)

# Directory for storing notes
NOTES_DIR = Path.home() / "Alejandro_notes"
NOTES_DIR.mkdir(exist_ok=True)

@screen_type
class BrainDumpScreen(Screen):
	"""Simple offline voice-to-file note-taking screen - no AI, just pure dictation"""

	def __init__(self, session: 'Session'):
		super().__init__(
			session=session,
			title="Brain Dump",
			controls=[
				session.make_back_control()
			])

		# State management
		self.current_filename: str = ""
		self.content_buffer: str = ""

	@control(
		keyphrases=["new note", "create file", "new file"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def new_note(self, control: ModalControl):
		"""Set filename for new note"""
		filename = control.collected_words.strip()
		if not filename:
			print("[BRAIN DUMP] No filename provided")
			return

		# Ensure it has an extension, default to .txt
		if '.' not in filename:
			filename = filename + ".txt"

		# Sanitize filename - replace spaces with underscores
		filename = filename.replace(' ', '_')

		self.current_filename = filename
		self.content_buffer = ""
		print(f"[BRAIN DUMP] New note: {filename}")

	@control(
		keyphrases=["begin dictation", "start dictating", "start writing"],
		deactivate_phrases=["end dictation", "stop dictating", "finished dictating", "done"]
	)
	def dictate_content(self, control: ModalControl):
		"""Accumulate note content across multiple dictation sessions"""
		dictated_text = control.collected_words.strip()
		if dictated_text:
			if self.content_buffer:
				self.content_buffer += " " + dictated_text
			else:
				self.content_buffer = dictated_text
			print(f"[BRAIN DUMP] Buffer ({len(self.content_buffer)} chars): {self.content_buffer[:100]}...")

	@control(keyphrases=["save", "save note", "save file"])
	def save_note(self, control: Control):
		"""Save current buffer to file"""
		if not self.current_filename:
			print("[BRAIN DUMP] No filename set. Say 'new note' first.")
			return

		if not self.content_buffer.strip():
			print("[BRAIN DUMP] Nothing to save - buffer is empty")
			return

		filepath = NOTES_DIR / self.current_filename

		try:
			with open(filepath, 'w') as f:
				f.write(self.content_buffer)
			print(f"[BRAIN DUMP] Saved {len(self.content_buffer)} chars to {filepath}")

			# Clear buffer after saving
			self.content_buffer = ""

		except Exception as e:
			print(f"[BRAIN DUMP ERROR] Failed to save: {e}")

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

		# Add extension if missing
		if '.' not in filename:
			filename = filename + ".txt"

		filename = filename.replace(' ', '_')

		filepath = NOTES_DIR / filename

		if not filepath.exists():
			print(f"[BRAIN DUMP] File not found: {filename}")
			return

		# Load existing content
		try:
			with open(filepath, 'r') as f:
				existing = f.read()

			self.current_filename = filename
			self.content_buffer = existing
			print(f"[BRAIN DUMP] Loaded {filename} ({len(existing)} chars). Begin dictating to append.")

		except Exception as e:
			print(f"[BRAIN DUMP ERROR] Failed to load: {e}")

	@control(keyphrases=["list notes", "show notes", "list files"])
	def list_notes(self, control: Control):
		"""List all saved notes"""
		notes = sorted([f.name for f in NOTES_DIR.iterdir() if f.is_file()])

		if not notes:
			print("[BRAIN DUMP] No notes found")
			return

		print(f"\n[BRAIN DUMP] Notes in {NOTES_DIR}:")
		for note in notes:
			filepath = NOTES_DIR / note
			size = filepath.stat().st_size
			print(f"  - {note} ({size} bytes)")
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

		if '.' not in filename:
			filename = filename + ".txt"

		filename = filename.replace(' ', '_')
		filepath = NOTES_DIR / filename

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

		if '.' not in filename:
			filename = filename + ".txt"

		filename = filename.replace(' ', '_')
		filepath = NOTES_DIR / filename

		if not filepath.exists():
			print(f"[BRAIN DUMP] File not found: {filename}")
			return

		try:
			filepath.unlink()
			print(f"[BRAIN DUMP] Deleted {filename}")

			# Clear state if we deleted the current file
			if self.current_filename == filename:
				self.current_filename = ""
				self.content_buffer = ""

		except Exception as e:
			print(f"[BRAIN DUMP ERROR] Failed to delete: {e}")

	@control(keyphrases=["clear buffer", "clear", "reset buffer", "start over"])
	def clear_buffer(self, control: Control):
		"""Clear the content buffer without saving"""
		self.content_buffer = ""
		print("[BRAIN DUMP] Buffer cleared")

	@control(keyphrases=["new session", "reset", "clear all"])
	def reset_session(self, control: Control):
		"""Reset filename and buffer"""
		self.current_filename = ""
		self.content_buffer = ""
		print("[BRAIN DUMP] Session reset")

	@control(keyphrases=["status", "current file", "what file"])
	def show_status(self, control: Control):
		"""Show current filename and buffer status"""
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
