import logging
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify
from threading import Thread
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Models.Conversation import Conversation, Message, Roles
from examples.smart_model import assistant_interaction_syntax
from Alejandro.Models.syntax_tree_requirement import SyntaxTreeValidatorRequirement
from Alejandro.web.events import push_event, ConversationUpdateEvent
from RequiredAI.helpers import get_msg_content
from RequiredAI.ModelConfig import InputConfig
from RequiredAI.RequirementTypes import WrittenRequirement, ContainsRequirement
from Alejandro.Core.Assistant import client, llama_70b, gpt_oss_20b, talk
from Alejandro.CodeRequirements import load_requirements, check, CheckResult
from assistant_interaction.utils import process_commands

bp = Blueprint('coder', __name__)
_log = logging.getLogger(__name__)

# ── Shared resources ──────────────────────────────────────────────────────────

_README_PATH = Path(__file__).parents[4] / "assistant_interaction" / "README.md"
_SYNTAX_DOCS = _README_PATH.read_text() if _README_PATH.exists() else ""

_script_requirements = [
	ContainsRequirement(
		value=["```txt\n<AI_RESPONSE>"],
		name="Must contain an AI response block"
	),
	SyntaxTreeValidatorRequirement(
		nodes=assistant_interaction_syntax,
		name="Assistant Interaction Syntax"
	),
]

# ── Models ────────────────────────────────────────────────────────────────────

# Talk: no input_config — sees the full conversation. Good for debugging
# what the other models did.
coder_talk = client.model(
	name="CoderTalk",
	base_model=llama_70b,
	requirements=talk.requirements,
	output_tags=["talk"]
)

# Explore: sees all transcribed user messages. Injected prompt gives syntax
# docs and asks for a read-only script to gather project context.
explore_model = client.model(
	name="CoderExplore",
	base_model=llama_70b,
	input_config=InputConfig(
		filter_tags=["transcribed"],
		messages_to_include=[(0, -1), {"role": "user", "content": (
			_SYNTAX_DOCS +
			"\n\nUsing the syntax above, write an AI script that reads the relevant "
			"files and directories to gather context for the user's request. "
			"Use AI_READ_FILE and AI_BASH_START only — do not write or modify any files."
		)}]
	),
	requirements=_script_requirements + [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Only use AI_READ_FILE and AI_BASH_START to gather information. Never use AI_SAVE_START or AI_APPLY_CHOICES."],
			positive_examples=[],
			negative_examples=[],
			name="Read only — no writes"
		),
	],
	output_tags=["explore"]
)

# Plan: sees all transcribed user messages + all exploration results.
# Injected prompt asks for prose-only planning, no code.
plan_model = client.model(
	name="CoderPlan",
	base_model=llama_70b,
	input_config=InputConfig(
		filter_tags=["transcribed", "explore_result"],
		messages_to_include=[(0, -1), {"role": "user", "content": (
			"Based on the user's request and the exploration results above, write a "
			"detailed prose plan describing exactly what code changes need to be made "
			"and why. No code blocks — prose only."
		)}]
	),
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Write a prose plan only. No code blocks. Describe what changes to make and why."],
			positive_examples=[],
			negative_examples=[],
			name="Prose plan, no code"
		),
	],
	output_tags=["plan"]
)

# Draft: sees all transcribed user messages + the plan.
# Injected prompt asks for Q&A pairs per change.
draft_model = client.model(
	name="CoderDraft",
	base_model=llama_70b,
	input_config=InputConfig(
		filter_tags=["transcribed", "plan"],
		messages_to_include=[(0, -1), {"role": "user", "content": (
			"Using the plan above, write out each code change as a Q&A pair. "
			"The question describes what to change; the answer shows the new content "
			"in a markdown code block labelled with the filename and line range."
		)}]
	),
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["For each change, write a Q&A pair: question states what to change, answer shows the new content in a markdown code block with filename and line range."],
			positive_examples=[],
			negative_examples=[],
			name="Q&A draft format"
		),
	],
	output_tags=["draft"]
)

# Script: sees plan + draft. Injected prompt gives syntax docs and asks to
# produce a full assistant_interaction script with saves and hunk choices.
script_model = client.model(
	name="CoderScript",
	base_model=llama_70b,
	input_config=InputConfig(
		filter_tags=["plan", "draft"],
		messages_to_include=[(0, -1), {"role": "user", "content": (
			_SYNTAX_DOCS +
			"\n\nUsing the syntax above, convert the Q&A draft into an "
			"assistant_interaction script. Save each changed file using AI_SAVE_START "
			"and present each diff hunk for review using AI_APPLY_CHOICES."
		)}]
	),
	requirements=_script_requirements + [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Use AI_SAVE_START to write file changes and AI_APPLY_CHOICES to present each diff hunk for review."],
			positive_examples=[],
			negative_examples=[],
			name="Produce script with saves and hunk choices"
		),
	],
	output_tags=["script"]
)

# Hunk validator: sees the script output + execution results (diffs + choices).
# Injected prompt gives syntax docs and asks for AI_APPLY_CHOICES decisions.
hunk_model = client.model(
	name="CoderHunks",
	base_model=llama_70b,
	input_config=InputConfig(
		filter_tags=["script", "script_result"],
		messages_to_include=[(0, -1), {"role": "user", "content": (
			_SYNTAX_DOCS +
			"\n\nFor each file with change hunks shown above, write an AI_APPLY_CHOICES "
			"block accepting or rejecting each hunk. Accept hunks that correctly implement "
			"the intended change; reject those that introduce errors or unnecessary changes."
		)}]
	),
	requirements=_script_requirements + [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["For each file with choice blocks, produce an AI_APPLY_CHOICES block with Yes or No for each numbered hunk."],
			positive_examples=[],
			negative_examples=[],
			name="Apply choices per hunk"
		),
	],
	output_tags=["hunks"]
)

# ── Screen ────────────────────────────────────────────────────────────────────

@screen_type
class CoderScreen(Screen):
	"""
	Voice-driven coding screen with rolling transcription buffer.

	The user speaks into a rolling transcription buffer, then fires one of
	several controls to act on that buffer:

	  Start Speaking / Stop Speaking  — append spoken words to the buffer
	  Clear                           — wipe the buffer
	  Send                            — conversational reply (CoderTalk model,
	                                    sees full conversation — useful for
	                                    debugging what all other models did)
	  Make Code Change                — full exploration → planning → drafting
	                                    → script generation → hunk validation
	  Apply                           — same chain but skip exploration
	                                    (assumes context already loaded)
	  Explore / Load                  — exploration step only (gather context)
	"""

	def __init__(self, session: 'Session', project_dir: str | None = None):
		super().__init__(session=session, title="Coder", controls=[session.make_back_control()])
		self._session = session
		self._buffer: list[str] = []
		self._conversation = Conversation(name="Coder Session")
		self._conversation.save()
		self._is_processing = False
		self._project_dir = project_dir  # git repo root for post-apply requirements checking

	@property
	def buffer_text(self) -> str:
		return " ".join(self._buffer)

	def _append_msg(self, response, model) -> None:
		"""Append a model response to the conversation and push an SSE update."""
		self._conversation.add_message(Message(
			role=Roles.ASSISTANT,
			content=get_msg_content(response),
			model_name=model.name,
			extra={"raw": response},
			tags=response.get('tags', [])
		))
		self._conversation.save()
		push_event(ConversationUpdateEvent(
			session_id=self._session.id,
			conversation_id=self._conversation.id,
			data=self._conversation.to_dict()
		))

	def _run_requirements_check(self) -> None:
		"""
		After code changes are applied, run all CodeRequirements against the
		project diff and append a summary to the conversation.

		Loads requirements from:
		  1. ~/.alejandro/code_requirements/  (global user rules)
		  2. <project_dir>/.code_requirements/  (per-project rules)

		Skipped silently if project_dir is not set.
		"""
		if not self._project_dir:
			return

		requirements = load_requirements(
			directory=str(Path.home() / ".alejandro" / "code_requirements"),
		) + load_requirements(
			directory=str(Path(self._project_dir) / ".code_requirements"),
		)

		if not requirements:
			return

		result = check(
			requirements=requirements,
			project_dir=self._project_dir,
			conversation=self._conversation.to_messages(),
			client=client,
		)

		lines = [
			f"**Requirements check**: {'PASSED' if result.all_passed else 'FAILED'}",
			"",
		]
		for r in result.results:
			if not r.pertinent.passed:
				lines.append(f"- ⬜ {r.name} — not pertinent ({r.pertinent.reason})")
			elif r.validate and r.validate.passed:
				lines.append(f"- ✅ {r.name} — {r.validate.reason}")
			elif r.validate:
				lines.append(f"- ❌ {r.name} — {r.validate.reason}")
			else:
				lines.append(f"- ⚠️ {r.name} — validate not run")

		self._append_tool_result("\n".join(lines), "requirements_result")

	def _append_tool_result(self, content: str, tag: str) -> None:
		"""Append a tool execution result to the conversation with a tag."""
		self._conversation.add_message(Message(role=Roles.USER, content=content, tags=[tag]))
		self._conversation.save()
		push_event(ConversationUpdateEvent(
			session_id=self._session.id,
			conversation_id=self._conversation.id,
			data=self._conversation.to_dict()
		))

	def _take_buffer(self) -> bool:
		"""Commit buffer to conversation as a transcribed user message. Returns False if nothing to do."""
		if not self.buffer_text.strip() or self._is_processing:
			return False
		self._conversation.add_message(Message(role=Roles.USER, content=self.buffer_text, tags=["transcribed"]))
		self._conversation.save()
		push_event(ConversationUpdateEvent(
			session_id=self._session.id,
			conversation_id=self._conversation.id,
			data=self._conversation.to_dict()
		))
		self._buffer.clear()
		self._is_processing = True
		return True

	# ── Controls ──────────────────────────────────────────────────────────────

	@control(text="Start Speaking",
	         keyphrases=["start speaking", "begin speaking"],
	         deactivate_phrases=["stop speaking", "end speaking", "done speaking", "stop"],
	         js_return_handler="updateBuffer")
	def speak(self, control: ModalControl) -> str:
		words = control.collected_words.strip()
		if words:
			self._buffer.append(words)
		return self.buffer_text

	@control(keyphrases=["clear", "clear buffer", "start over", "reset buffer"],
	         js_return_handler="updateBuffer")
	def clear(self, control: Control) -> str:
		self._buffer.clear()
		return ""

	@control(keyphrases=["send", "send message", "chat", "ask"])
	def send(self, control: Control) -> None:
		if not self._take_buffer():
			return
		def run():
			try:
				self._append_msg(coder_talk(self._conversation.to_messages()), coder_talk)
			except Exception as e:
				_log.error("[CODER send] %s", e, exc_info=True)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["make code change", "code change", "make change", "change code", "implement"])
	def make_code_change(self, control: Control) -> None:
		if not self._take_buffer():
			return
		def run():
			try:
				# Stage 1: Exploration
				explore_response = explore_model(self._conversation.to_messages())
				self._append_msg(explore_response, explore_model)
				explore_result = process_commands(get_msg_content(explore_response))
				if explore_result:
					self._append_tool_result(explore_result, "explore_result")

				# Stage 2: Plan
				self._append_msg(plan_model(self._conversation.to_messages()), plan_model)

				# Stage 3: Draft
				self._append_msg(draft_model(self._conversation.to_messages()), draft_model)

				# Stage 4: Script generation
				script_response = script_model(self._conversation.to_messages())
				self._append_msg(script_response, script_model)
				script_result = process_commands(get_msg_content(script_response))
				if script_result:
					self._append_tool_result(script_result, "script_result")

					# Stage 5: Hunk validation
					hunk_response = hunk_model(self._conversation.to_messages())
					self._append_msg(hunk_response, hunk_model)
					apply_result = process_commands(get_msg_content(hunk_response))
					if apply_result:
						self._append_tool_result(apply_result, "apply_result")
						# Stage 6: Requirements check against the resulting diff
						self._run_requirements_check()
			except Exception as e:
				_log.error("[CODER make_code_change] %s", e, exc_info=True)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["apply", "apply changes", "apply to code"])
	def apply(self, control: Control) -> None:
		"""Skip exploration; plan → draft → script → hunk validation using existing context."""
		if not self._take_buffer():
			return
		def run():
			try:
				self._append_msg(plan_model(self._conversation.to_messages()), plan_model)
				self._append_msg(draft_model(self._conversation.to_messages()), draft_model)

				script_response = script_model(self._conversation.to_messages())
				self._append_msg(script_response, script_model)
				script_result = process_commands(get_msg_content(script_response))
				if script_result:
					self._append_tool_result(script_result, "script_result")

					hunk_response = hunk_model(self._conversation.to_messages())
					self._append_msg(hunk_response, hunk_model)
					apply_result = process_commands(get_msg_content(hunk_response))
					if apply_result:
						self._append_tool_result(apply_result, "apply_result")
						# Stage 5: Requirements check against the resulting diff
						self._run_requirements_check()
			except Exception as e:
				_log.error("[CODER apply] %s", e, exc_info=True)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["explore", "load", "load context", "explore codebase", "gather context"])
	def explore(self, control: Control) -> None:
		"""Exploration step only — AI reads files and gathers context into the conversation."""
		if not self._take_buffer():
			return
		def run():
			try:
				explore_response = explore_model(self._conversation.to_messages())
				self._append_msg(explore_response, explore_model)
				explore_result = process_commands(get_msg_content(explore_response))
				if explore_result:
					self._append_tool_result(explore_result, "explore_result")
			except Exception as e:
				_log.error("[CODER explore] %s", e, exc_info=True)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	def get_template_data(self):
		return {'conversation_id': self._conversation.id}


# ── Routes ────────────────────────────────────────────────────────────────────

@bp.route(f'/{CoderScreen.url()}')
def show_screen() -> str:
	session_id = request.args.get('session')
	session = get_or_create_session(session_id)
	screen = session.current_or_get(CoderScreen)
	return render_template('coder.html', screen=screen,
	                       session_id=session.id, **screen.get_template_data())

@bp.route('/coder_data', methods=['POST'])
def coder_data():
	data = request.get_json()
	return jsonify({'data': Conversation.load(data.get('conversation_id'))})
