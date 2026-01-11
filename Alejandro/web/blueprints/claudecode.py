import subprocess
import threading
from typing import List, Dict, Optional
from flask import Blueprint, render_template, request
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.helpers import get_msg_content
from Alejandro.Core.Assistant import client, gpt_oss_120b
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control, ModalControl
from Alejandro.Core.Control import Control

bp = Blueprint('claudecode', __name__)

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
			# Format: alternating user/assistant messages
			conversation_args = []
			for msg in self.conversation_history[-10:]:  # Last 10 messages for context
				if msg["role"] == "user":
					conversation_args.extend(["--message", msg["content"]])

			# Call Claude Code CLI
			cmd = ["/opt/node22/bin/claude"] + conversation_args

			print(f"[CLAUDE CODE] Running: {' '.join(cmd[:3])}...")

			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=300  # 5 minute timeout
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
