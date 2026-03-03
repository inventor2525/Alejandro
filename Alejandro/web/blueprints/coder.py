from flask import Blueprint, render_template, request, jsonify
from threading import Thread
from typing import List

from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.web.events import push_event, ConversationUpdateEvent
from RequiredAI.helpers import get_msg_content

bp = Blueprint('coder', __name__)


@screen_type
class CoderScreen(Screen):
	"""
	Voice-driven coding screen.

	The user speaks into a rolling transcription buffer, then fires one of
	several controls to act on that buffer:

	  Start Speaking / Stop Speaking  — append spoken words to the buffer
	  Clear                           — wipe the buffer
	  Send                            — conversational reply (Talk model)
	  Make Code Change                — full exploration→drafting→script chain
	  Apply                           — same chain but skip exploration
	  Explore / Load                  — exploration step only (gather context)
	"""

	def __init__(self, session: 'Session'):
		super().__init__(
			session=session,
			title="Coder",
			controls=[session.make_back_control()]
		)
		self._session = session
		self._buffer: List[str] = []
		self._conversation = Conversation(name="Coder Session")
		self._conversation.save()
		self._is_processing = False

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	@property
	def buffer_text(self) -> str:
		"""Full accumulated transcription buffer as a single string."""
		return " ".join(self._buffer)

	def _push_conversation_update(self) -> None:
		push_event(ConversationUpdateEvent(
			session_id=self._session.id,
			conversation_id=self._conversation.id,
			data=self._conversation.to_dict()
		))

	def _dispatch(self, model_name: str) -> None:
		"""
		Move the buffer into the conversation as a user message, clear it,
		and start a background thread to call the given model.
		"""
		if not self.buffer_text.strip() or self._is_processing:
			return
		message = self.buffer_text
		self._buffer.clear()
		self._is_processing = True
		Thread(target=self._run_model, args=(message, model_name), daemon=True).start()

	def _run_model(self, user_message: str, model_name: str) -> None:
		"""Background thread: call model, append response to conversation."""
		from Alejandro.Core.Assistant import client

		user_msg = Message(role=Roles.USER, content=user_message)
		self._conversation.add_message(user_msg)
		self._conversation.save()
		self._push_conversation_update()

		ai_msg = None
		try:
			messages = [
				{
					"role": msg.role.lower(),
					"content": msg.content,
					**({"tags": msg.tags} if msg.tags else {})
				}
				for msg in self._conversation.messages
			]
			response = client.create_completion(model=model_name, messages=messages)
			ai_msg = Message(
				role=Roles.ASSISTANT,
				content=get_msg_content(response),
				model_name=model_name,
				extra={"raw": response},
				tags=response.get('tags', [])
			)
		except Exception as e:
			print(f"[CODER] Model error ({model_name}): {e}")
			ai_msg = Message(
				role=Roles.ASSISTANT,
				content=f"[Error from {model_name}: {e}]",
				model_name=model_name
			)
		finally:
			self._is_processing = False

		self._conversation.add_message(ai_msg)
		self._conversation.save()
		self._push_conversation_update()

	# ------------------------------------------------------------------
	# Controls
	# ------------------------------------------------------------------

	@control(
		text="Start Speaking",
		keyphrases=["start speaking", "begin speaking"],
		deactivate_phrases=["stop speaking", "end speaking", "done speaking", "stop"],
		js_return_handler="updateBuffer"
	)
	def speak(self, control: ModalControl) -> str:
		"""Append this speaking session's words to the rolling buffer."""
		words = control.collected_words.strip()
		if words:
			self._buffer.append(words)
		return self.buffer_text

	@control(
		keyphrases=["clear", "clear buffer", "start over", "reset buffer"],
		js_return_handler="updateBuffer"
	)
	def clear(self, control: Control) -> str:
		"""Wipe the transcription buffer."""
		self._buffer.clear()
		return ""

	@control(keyphrases=["send", "send message", "chat", "ask"])
	def send(self, control: Control) -> None:
		"""Send the buffer to the conversational Talk model."""
		self._dispatch("Talk")

	@control(keyphrases=["make code change", "code change", "make change", "change code", "implement"])
	def make_code_change(self, control: Control) -> None:
		"""
		Send the buffer through the full coding chain:
		exploration → planning → drafting → script generation.

		TODO: replace SmartModel with the full CodingModel once implemented.
		"""
		self._dispatch("SmartModel")

	@control(keyphrases=["apply", "apply changes", "apply to code"])
	def apply(self, control: Control) -> None:
		"""
		Send the buffer to the coding chain, skipping exploration.
		Assumes context is already loaded from a prior Explore call.

		TODO: replace SmartModel with an ApplyModel (no exploration step).
		"""
		self._dispatch("SmartModel")

	@control(keyphrases=["explore", "load", "load context", "explore codebase", "gather context"])
	def explore(self, control: Control) -> None:
		"""
		Run only the exploration step: gather context without making changes.

		TODO: replace SmartModel with an ExplorationModel (read-only).
		"""
		self._dispatch("SmartModel")

	# ------------------------------------------------------------------
	# Template
	# ------------------------------------------------------------------

	def get_template_data(self):
		return {'conversation_id': self._conversation.id}


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@bp.route(f'/{CoderScreen.url()}')
def show_screen() -> str:
	session_id = request.args.get('session')
	session = get_or_create_session(session_id)
	screen = session.current_or_get(CoderScreen)
	return render_template(
		'coder.html',
		screen=screen,
		session_id=session.id,
		**screen.get_template_data()
	)


@bp.route('/coder_data', methods=['POST'])
def coder_data():
	"""Fetch initial conversation data for the coder screen."""
	data = request.get_json()
	conversation_id = data.get('conversation_id')
	return jsonify({'data': Conversation.load(conversation_id)})
