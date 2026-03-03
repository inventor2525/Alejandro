from flask import Blueprint, render_template, request, jsonify
from threading import Thread
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.web.events import push_event, ConversationUpdateEvent
from RequiredAI.helpers import get_msg_content
from RequiredAI.ModelConfig import InputConfig
from RequiredAI.RequirementTypes import WrittenRequirement
from Alejandro.Core.Assistant import client, llama_70b, gpt_oss_20b, talk

bp = Blueprint('coder', __name__)

# ── Stage models ──────────────────────────────────────────────────────────────
# client.model() lazily creates and registers each model with the RequiredAI
# server on first import; subsequent imports return the cached instance.
# InputConfig.filter_tags controls which prior messages each stage sees;
# output_tags mark each response so later stages can filter to it.

explore_model = client.model(
	name="CoderExplore",
	base_model=llama_70b,
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Only gather information. Do not write or modify any files."],
			positive_examples=[],
			negative_examples=[],
			name="Read only"
		)
	],
	output_tags=["explore"]
)

plan_model = client.model(
	name="CoderPlan",
	base_model=llama_70b,
	# sees: user messages (untagged) + explore output
	input_config=InputConfig(filter_tags=["explore", None]),
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Write a prose plan only. No code blocks. Describe what changes to make and why."],
			positive_examples=[],
			negative_examples=[],
			name="Prose plan, no code"
		)
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
		)
	],
	output_tags=["draft"]
)

script_model = client.model(
	name="CoderScript",
	base_model=llama_70b,
	# sees: plan + draft only — enough context, no raw user messages needed
	input_config=InputConfig(filter_tags=["plan", "draft"]),
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Convert the Q&A pairs into an assistant_interaction script using the correct syntax markers."],
			positive_examples=[],
			negative_examples=[],
			name="assistant_interaction script"
		)
	],
	output_tags=["script"]
)

# ── Screen ────────────────────────────────────────────────────────────────────

@screen_type
class CoderScreen(Screen):
	"""Voice-driven coding screen with rolling transcription buffer."""

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

	def _msgs(self) -> list[dict]:
		"""Full conversation as RequiredAI message dicts (tags forwarded when present)."""
		return [
			{"role": msg.role.lower(), "content": msg.content,
			 **({"tags": msg.tags} if msg.tags else {})}
			for msg in self._conversation.messages
		]

	def _record(self, response, model) -> None:
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
				self._record(talk(self._msgs()), talk)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["make code change", "code change", "make change", "change code", "implement"])
	def make_code_change(self, control: Control) -> None:
		if not self._take_buffer():
			return
		def run():
			try:
				self._record(explore_model(self._msgs()), explore_model)
				self._record(plan_model(self._msgs()), plan_model)
				self._record(draft_model(self._msgs()), draft_model)
				self._record(script_model(self._msgs()), script_model)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["apply", "apply changes", "apply to code"])
	def apply(self, control: Control) -> None:
		"""Skip exploration; plan → draft → script using existing context."""
		if not self._take_buffer():
			return
		def run():
			try:
				self._record(plan_model(self._msgs()), plan_model)
				self._record(draft_model(self._msgs()), draft_model)
				self._record(script_model(self._msgs()), script_model)
			finally:
				self._is_processing = False
		Thread(target=run, daemon=True).start()

	@control(keyphrases=["explore", "load", "load context", "explore codebase", "gather context"])
	def explore(self, control: Control) -> None:
		"""Exploration step only — read files and gather context."""
		if not self._take_buffer():
			return
		def run():
			try:
				self._record(explore_model(self._msgs()), explore_model)
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
