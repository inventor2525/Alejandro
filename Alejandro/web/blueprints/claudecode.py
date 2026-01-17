import subprocess
import threading
import shutil
import random
from pathlib import Path
from typing import List, Dict, Optional
from flask import Blueprint, render_template, request
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.helpers import get_msg_content
from Alejandro.Core.Assistant import client, gpt_oss_120b
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control, ModalControl
from Alejandro.Core.Control import Control

bp = Blueprint('claudecode', __name__)

# Base directories
NOTES_DIR = Path.home() / "Documents" / "Alejandro" / "Notes"
REPOS_DIR = Path.home() / "Documents" / "Alejandro" / "repos"
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# Speakable UUID word lists
ADJECTIVES = [
	"quick", "blue", "red", "green", "bright", "dark", "fast", "slow", "big", "small",
	"cool", "warm", "old", "new", "long", "short", "high", "low", "deep", "wide"
]
NOUNS = [
	"fox", "wolf", "bear", "hawk", "lion", "tiger", "eagle", "shark", "horse", "whale",
	"tree", "star", "moon", "sun", "wave", "rock", "cloud", "wind", "fire", "snow"
]

def generate_speakable_uuid() -> str:
	"""Generate a short, easily speakable branch name like 'quick-fox-42'"""
	adj = random.choice(ADJECTIVES)
	noun = random.choice(NOUNS)
	num = random.randint(10, 99)
	return f"{adj}-{noun}-{num}"

@screen_type
class ClaudeCodeScreen(Screen):
	"""Screen for interacting with Claude Code CLI"""

	def __init__(self, session: 'Session'):
		super().__init__(
			session=session,
			title="Claude Code",
			controls=[
				session.make_back_control()
			])

		# State management
		self.dictation_buffer: str = ""
		self.conversation_history: List[Dict[str, str]] = []
		self.last_claude_response: Optional[str] = None
		self.current_repo_path: Optional[Path] = None
		self.current_branch: Optional[str] = None

		# Define summarizer model inline with requirements
		self.summarizer = client.model(base_model=gpt_oss_120b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Do not use markdown formatting. No backticks, no code blocks, no headers, no bold, no italics."],
				negative_examples=["```python", "## Summary", "**bold text**", "*italic*", "# Header"],
				name="No Markdown"
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Use short, direct sentences as if speaking on a phone call. Be conversational and personable."],
				positive_examples=["I ran the build script. Found three errors. Fixed the authentication bug."],
				negative_examples=[
					"After careful analysis of the codebase, I proceeded to execute...",
					"I have successfully completed the following tasks:",
					"Let me explain what happened in detail..."
				],
				name="Conversational Phone Style"
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Focus on actions taken, not code details. Assume the listener cannot see a screen and is driving."],
				positive_examples=["Modified the login function to hash passwords.", "Updated three files in the auth module."],
				negative_examples=[
					"Changed line 42 from bcrypt.hash() to argon2.hash()",
					"Modified the function signature to include the new parameter",
					"The code now looks like this..."
				],
				name="Action-Oriented Summary"
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Be concise. Three to five sentences maximum per topic. Get to the point quickly."],
				positive_examples=["Fixed the bug. Tests pass now. Ready to deploy."],
				negative_examples=["I've completed an extensive analysis of the issue and after thorough investigation..."],
				name="Brief Summary"
			)
		])

	@control(
		keyphrases=["new from notes", "create from notes", "new project from notes"],
		deactivate_phrases=["done", "finished", "end"]
	)
	def new_from_notes(self, control: ModalControl):
		"""Create a new repo from a notes directory"""
		notes_path = control.collected_words.strip()
		if not notes_path:
			print("[CLAUDE CODE] No notes path provided")
			return

		# Replace spoken "slash" with actual slash
		notes_path = notes_path.replace(' slash ', '/')
		notes_path = notes_path.replace('slash ', '/')
		notes_path = notes_path.replace(' slash', '/')
		notes_path = notes_path.strip('/')

		# Validate path exists
		source_dir = NOTES_DIR / notes_path
		if not source_dir.exists() or not source_dir.is_dir():
			print(f"[CLAUDE CODE] Notes directory not found: {notes_path}")
			return

		# Get repo name from last folder in path
		repo_name = Path(notes_path).name
		repo_path = REPOS_DIR / repo_name

		# Generate speakable branch name
		branch_name = generate_speakable_uuid()

		print(f"[CLAUDE CODE] Creating repo '{repo_name}' from notes '{notes_path}'")
		print(f"[CLAUDE CODE] Branch: {branch_name}")

		# Run in background
		thread = threading.Thread(target=self._create_repo_from_notes, args=(source_dir, repo_path, repo_name, branch_name))
		thread.daemon = True
		thread.start()

	def _create_repo_from_notes(self, source_dir: Path, repo_path: Path, repo_name: str, branch_name: str):
		"""Create or update repository with notes"""
		try:
			if not repo_path.exists():
				# New repo: create, init, instructions commit, branch, copy notes
				print(f"[CLAUDE CODE] Creating new repository: {repo_name}")
				repo_path.mkdir(parents=True, exist_ok=True)

				# Git init
				subprocess.run(["git", "init"], cwd=repo_path, check=True)
				subprocess.run(["git", "config", "user.name", "Alejandro Claude Code"], cwd=repo_path, check=True)
				subprocess.run(["git", "config", "user.email", "claudecode@alejandro.local"], cwd=repo_path, check=True)

				# Create initial README with instructions
				readme_path = repo_path / "README.md"
				with open(readme_path, 'w') as f:
					f.write(f"""# {repo_name}

## Instructions for Claude Code

This repository contains design documents and notes in the `notes/` directory.

### How to Read the Notes

1. Notes are in markdown format with the following structure:
   - `# Note Content` - Contains the design documentation and requirements
   - `# Change Log` - CSV log of when content was added (for audio traceability)

2. Each note may contain:
   - User-defined headers (## level)
   - Design specifications
   - Requirements
   - Implementation ideas

3. Your task is to implement drafts based on these design documents.

4. Each branch represents a separate draft attempt - they are independent explorations.

### Workflow

- Read all notes in the `notes/` directory
- Understand the requirements and design intent
- Implement your draft in this repository
- This branch ({branch_name}) is your workspace for this draft
""")

				# Initial commit
				subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
				subprocess.run(["git", "commit", "-m", "initial commit with instructions"], cwd=repo_path, check=True)

				print(f"[CLAUDE CODE] Created initial commit")

			# Branch from first commit
			print(f"[CLAUDE CODE] Creating branch: {branch_name}")
			subprocess.run(["git", "checkout", "-b", branch_name, "HEAD"], cwd=repo_path, check=True)

			# Copy notes to branch
			notes_dest = repo_path / "notes"
			if notes_dest.exists():
				shutil.rmtree(notes_dest)

			shutil.copytree(source_dir, notes_dest)

			# Commit notes
			subprocess.run(["git", "add", "notes/"], cwd=repo_path, check=True)
			subprocess.run(["git", "commit", "-m", f"added design notes from {source_dir.name}"], cwd=repo_path, check=True)

			print(f"[CLAUDE CODE] Repository ready: {repo_path}")
			print(f"[CLAUDE CODE] Branch: {branch_name}")
			print(f"[CLAUDE CODE] Notes copied and committed")

			# Update state
			self.current_repo_path = repo_path
			self.current_branch = branch_name

			# Clear conversation for fresh start
			self.conversation_history = []
			self.dictation_buffer = ""

		except Exception as e:
			print(f"[CLAUDE CODE ERROR] Failed to create repo: {e}")

	@control(
		keyphrases=["begin dictation", "start dictating", "start input"],
		deactivate_phrases=["end dictation", "stop dictating", "finished dictating"]
	)
	def begin_dictation(self, control: ModalControl):
		"""Accumulate dictated text across multiple sessions"""
		dictated_text = control.collected_words.strip()
		if dictated_text:
			if self.dictation_buffer:
				self.dictation_buffer += " " + dictated_text
			else:
				self.dictation_buffer = dictated_text
			print(f"[DICTATION] Accumulated: {self.dictation_buffer}")

	@control(keyphrases=["send to claude", "send message", "submit to claude", "send"])
	def send_to_claude(self, control: Control):
		"""Send accumulated dictation to Claude Code CLI"""
		if not self.dictation_buffer.strip():
			print("[CLAUDE CODE] No dictation to send")
			return

		user_message = self.dictation_buffer
		print(f"\n[CLAUDE CODE] Sending to Claude: {user_message}")

		# Add to conversation history
		self.conversation_history.append({
			"role": "user",
			"content": user_message
		})

		# Clear buffer after sending
		self.dictation_buffer = ""

		# Call Claude Code in background thread
		thread = threading.Thread(target=self._call_claude_code, args=(user_message,))
		thread.daemon = True
		thread.start()

	def _call_claude_code(self, message: str):
		"""Call Claude Code CLI and capture response"""
		try:
			# Build conversation context for Claude Code
			conversation_args = []
			for msg in self.conversation_history[-10:]:  # Last 10 messages for context
				if msg["role"] == "user":
					conversation_args.extend(["--message", msg["content"]])

			# Build command with working directory if repo is set
			cmd = ["/opt/node22/bin/claude"] + conversation_args
			cwd = self.current_repo_path if self.current_repo_path else None

			if cwd:
				print(f"[CLAUDE CODE] Running in repo: {cwd.name} (branch: {self.current_branch})")
			print(f"[CLAUDE CODE] Running: {' '.join(cmd[:3])}...")

			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=300,  # 5 minute timeout
				cwd=cwd
			)

			if result.returncode == 0:
				response = result.stdout.strip()
				self.last_claude_response = response

				# Add to conversation history
				self.conversation_history.append({
					"role": "assistant",
					"content": response
				})

				print(f"\n[CLAUDE CODE RESPONSE]\n{response}\n")
			else:
				error_msg = result.stderr.strip() or "Unknown error"
				print(f"[CLAUDE CODE ERROR] {error_msg}")
				self.last_claude_response = f"Error: {error_msg}"

		except subprocess.TimeoutExpired:
			print("[CLAUDE CODE ERROR] Request timed out after 5 minutes")
			self.last_claude_response = "Error: Request timed out"
		except Exception as e:
			print(f"[CLAUDE CODE ERROR] {str(e)}")
			self.last_claude_response = f"Error: {str(e)}"

	@control(keyphrases=["summarize that", "give me summary", "summarize response", "summarize"])
	def summarize_response(self, control: Control):
		"""Summarize the last Claude Code response"""
		if not self.last_claude_response:
			print("[SUMMARIZE] No Claude Code response to summarize")
			return

		print("[SUMMARIZE] Generating summary of last response...")

		# Run summarization in background
		thread = threading.Thread(target=self._summarize, args=(self.last_claude_response,))
		thread.daemon = True
		thread.start()

	def _summarize(self, text: str):
		"""Generate summary using the summarizer model"""
		try:
			prompt = f"Summarize this response as if explaining it to someone on a phone call who can't see the screen:\n\n{text}"

			response = self.summarizer([{"role": "user", "content": prompt}])
			summary = get_msg_content(response).strip()

			print(f"\n[SUMMARY]\n{summary}\n")

		except Exception as e:
			print(f"[SUMMARIZE ERROR] {str(e)}")

	@control(keyphrases=["what did I say", "where was I", "what was I saying", "recap my input"])
	def self_summarize(self, control: Control):
		"""Summarize what the user has said in the conversation"""
		if not self.conversation_history:
			print("[SELF SUMMARIZE] No conversation history yet")
			return

		# Extract just user messages
		user_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]

		if not user_messages:
			print("[SELF SUMMARIZE] No user messages to summarize")
			return

		print("[SELF SUMMARIZE] Generating summary of your input...")

		# Run in background
		thread = threading.Thread(target=self._self_summarize, args=(user_messages,))
		thread.daemon = True
		thread.start()

	def _self_summarize(self, user_messages: List[str]):
		"""Generate summary of user's conversation"""
		try:
			combined = "\n\n".join(user_messages)
			prompt = f"Summarize what the user has been asking about or discussing:\n\n{combined}"

			response = self.summarizer([{"role": "user", "content": prompt}])
			summary = get_msg_content(response).strip()

			print(f"\n[SELF SUMMARY] You've been saying:\n{summary}\n")

		except Exception as e:
			print(f"[SELF SUMMARIZE ERROR] {str(e)}")

	@control(keyphrases=["clear dictation", "wipe dictation", "reset input", "start over"])
	def clear_dictation(self, control: Control):
		"""Clear the accumulated dictation buffer"""
		self.dictation_buffer = ""
		print("[DICTATION] Buffer cleared")

	@control(keyphrases=["clear chat", "clear conversation", "reset conversation", "new chat"])
	def clear_chat(self, control: Control):
		"""Clear conversation history"""
		self.conversation_history = []
		self.last_claude_response = None
		self.dictation_buffer = ""
		print("[CLAUDE CODE] Conversation history cleared")

	@control(keyphrases=["repo status", "current repo", "what repo", "where am i working"])
	def repo_status(self, control: Control):
		"""Show current repository and branch"""
		if self.current_repo_path:
			print(f"[CLAUDE CODE] Repository: {self.current_repo_path.name}")
			print(f"[CLAUDE CODE] Branch: {self.current_branch}")
			print(f"[CLAUDE CODE] Path: {self.current_repo_path}")
		else:
			print("[CLAUDE CODE] No repository set - working in default mode")

@bp.route(f'/{ClaudeCodeScreen.url()}')
def show_screen() -> str:
	"""Generic screen route handler"""
	session_id = request.args.get('session')

	session = get_or_create_session(session_id)
	screen = session.current_or_get(ClaudeCodeScreen)
	return render_template(
		'base.html',
		screen=screen,
		session_id=session.id,
		**screen.get_template_data()
	)
