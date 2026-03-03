import re
from flask import Blueprint, render_template, request, jsonify
from threading import Thread
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.Models.assistant_interaction_syntax import assistant_interaction_syntax
from Alejandro.Models.syntax_tree_requirement import SyntaxTreeValidatorRequirement
from Alejandro.web.events import push_event, ConversationUpdateEvent
from RequiredAI.helpers import get_msg_content
from RequiredAI.ModelConfig import InputConfig
from RequiredAI.RequirementTypes import WrittenRequirement, ContainsRequirement
from Alejandro.Core.Assistant import client, llama_70b, gpt_oss_20b, talk
from assistant_interaction.utils import process_commands

bp = Blueprint('coder', __name__)

# ── Syntax node requirements ──────────────────────────────────────────────────
# Locate the bash node in the shared syntax tree and add run-time restrictions.

def _find_node(nodes, start_regex):
	for node in nodes:
		if node.start_regex == start_regex:
			return node
		found = _find_node(node.children, start_regex)
		if found:
			return found
	return None

_bash_node = _find_node(assistant_interaction_syntax, r"^\s*### AI_BASH_START.*$")
if _bash_node:
	_bash_node.requirements = [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not include git push commands.", "Do not push code to remote repositories in ANY way."],
			positive_examples=['git commit -m "A commit"'],
			negative_examples=["git push origin main"],
			name="Never push to remote"
		),
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not source PyEnvironment, pyenv, or run pyenv activate."],
			positive_examples=["pip install numpy"],
			negative_examples=["source ~/.pyenv/bin/activate"],
			name="No PyEnvironment"
		),
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not run any python file."],
			positive_examples=["echo 'Done'"],
			negative_examples=["python script.py"],
			name="Do not run python files"
		),
	]

# ── Stage models ──────────────────────────────────────────────────────────────

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

explore_model = client.model(
	name="CoderExplore",
	base_model=llama_70b,
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

plan_model = client.model(
	name="CoderPlan",
	base_model=llama_70b,
	# sees: user messages (untagged) + explore output + explore tool results
	input_config=InputConfig(filter_tags=["explore", "explore_result", None]),
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

draft_model = client.model(
	name="CoderDraft",
	base_model=llama_70b,
	# sees: user messages (untagged) + plan output
	input_config=InputConfig(filter_tags=["plan", None]),
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["For each change, write a Q&A pair: the question states what to change, the answer shows the new content in a markdown code block labelled with filename and line range."],
			positive_examples=[],
			negative_examples=[],
			name="Q&A draft format"
		),
	],
	output_tags=["draft"]
)

script_model = client.model(
	name="CoderScript",
	base_model=llama_70b,
	# sees: plan + draft only — sufficient context for script generation
	input_config=InputConfig(filter_tags=["plan", "draft"]),
	requirements=_script_requirements + [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Convert the Q&A pairs into an assistant_interaction script. Use AI_SAVE_START to write file changes and AI_APPLY_CHOICES to present each hunk for review."],
			positive_examples=[],
			negative_examples=[],
			name="Produce assistant_interaction script with hunks"
		),
	],
	output_tags=["script"]
)

hunk_model = client.model(
	name="CoderHunks",
	base_model=llama_70b,
	# sees: the script + the execution output (diffs + choice blocks)
	input_config=InputConfig(filter_tags=["script", "script_result"]),
	requirements=_script_requirements + [
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["For each file with hunk choices, produce an AI_APPLY_CHOICES block. Accept hunks that correctly implement the intended change; reject those that do not."],
			positive_examples=[],
			negative_examples=[],
			name="Apply choices per hunk"
		),
	],
	output_tags=["hunks"]
)

# ── Script execution helper ───────────────────────────────────────────────────

def _run_script(content: str) -> str | None:
	"""Extract the <AI_RESPONSE>...<END_OF_INPUT> block and run it."""
	match = re.search(r'(<AI_RESPONSE>.*?<END_OF_INPUT>)', content, re.DOTALL)
	if not match:
		return None
	return process_commands(match.group(1))

# ── Screen ────────────────────────────────────────────────────────────────────

@screen_type
class CoderScreen(Screen):
	"""
	Voice-driven coding screen with rolling transcription buffer.

	The user speaks into a rolling transcription buffer, then fires one of
	several controls to act on that buffer:

	  Start Speaking / Stop Speaking  — append spoken words to the buffer
	  Clear                           — wipe the buffer
	  Send                            — conversational reply (Talk model)
	  Make Code Change                — full exploration → planning → drafting
	                                    → script generation → hunk validation
	  Apply                           — same chain but skip exploration
	                                    (assumes context already loaded)
	  Explore / Load                  — exploration step only (gather context)
	"""

	def __init__(self, session: 'Session'):
		super().__init__(session=session, title="Coder", controls=[session.make_back_control()])
		self._session = session
		self._buffer: list[str] = []
		self._conversation = Conversation(name="Coder Session")
		self._conversation.save()
		self._is_processing = False

	@property
	def buffer_text(self) -> str:
		return " ".join(self._buffer)

	def _pen_msg(self, response, model) -> None:
		"""Write a model response into the conversation and push an SSE update."""
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

	def _pen_tool_result(self, content: str, tag: str) -> None:
		"""Write a tool execution result into the conversation with a tag."""
		self._conversation.add_message(Message(role=Roles.USER, content=content, tags=[tag]))
		self._conversation.save()
		push_event(ConversationUpdateEvent(
			session_id=self._session.id,
			conversation_id=self._conversation.id,
			data=self._conversation.to_dict()
		))

	def _take_buffer(self) -> bool:
		"""Commit buffer to conversation as a user message. Returns False if nothing to do."""
		if not self.buffer_text.strip() or self._is_processing:
			return False
		self._conversation.add_message(Message(role=Roles.USER, content=self.buffer_text))
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
				self._pen_msg(talk(self._conversation.to_messages()), talk)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["make code change", "code change", "make change", "change code", "implement"])
	def make_code_change(self, control: Control) -> None:
		if not self._take_buffer():
			return
		def run():
			try:
				# Stage 1: Exploration — read files, gather context
				e_resp = explore_model(self._conversation.to_messages())
				self._pen_msg(e_resp, explore_model)
				e_result = _run_script(get_msg_content(e_resp))
				if e_result:
					self._pen_tool_result(e_result, "explore_result")

				# Stage 2: Plan — prose only, sees explore output
				self._pen_msg(plan_model(self._conversation.to_messages()), plan_model)

				# Stage 3: Draft — Q&A per change, sees plan
				self._pen_msg(draft_model(self._conversation.to_messages()), draft_model)

				# Stage 4: Script generation — assistant_interaction syntax, sees plan + draft
				s_resp = script_model(self._conversation.to_messages())
				self._pen_msg(s_resp, script_model)

				# Run the script: saves files, generates diffs + hunk choice blocks
				s_result = _run_script(get_msg_content(s_resp))
				if s_result:
					self._pen_tool_result(s_result, "script_result")

					# Stage 5: Hunk validation — AI accepts/rejects each diff hunk
					h_resp = hunk_model(self._conversation.to_messages())
					self._pen_msg(h_resp, hunk_model)

					# Apply the accepted hunks
					apply_result = _run_script(get_msg_content(h_resp))
					if apply_result:
						self._pen_tool_result(apply_result, "apply_result")
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
				self._pen_msg(plan_model(self._conversation.to_messages()), plan_model)
				self._pen_msg(draft_model(self._conversation.to_messages()), draft_model)

				s_resp = script_model(self._conversation.to_messages())
				self._pen_msg(s_resp, script_model)

				s_result = _run_script(get_msg_content(s_resp))
				if s_result:
					self._pen_tool_result(s_result, "script_result")

					h_resp = hunk_model(self._conversation.to_messages())
					self._pen_msg(h_resp, hunk_model)

					apply_result = _run_script(get_msg_content(h_resp))
					if apply_result:
						self._pen_tool_result(apply_result, "apply_result")
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["explore", "load", "load context", "explore codebase", "gather context"])
	def explore(self, control: Control) -> None:
		"""Exploration step only — read files and gather context into the conversation."""
		if not self._take_buffer():
			return
		def run():
			try:
				e_resp = explore_model(self._conversation.to_messages())
				self._pen_msg(e_resp, explore_model)
				e_result = _run_script(get_msg_content(e_resp))
				if e_result:
					self._pen_tool_result(e_result, "explore_result")
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
