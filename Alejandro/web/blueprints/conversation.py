from flask import Blueprint, render_template, request
from typing import Dict, Any, List
from datetime import datetime
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type
from Alejandro.Core.Control import Control
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Models.Conversation import Conversation, Message, Roles
from flask import jsonify

bp = Blueprint('conversation', __name__)

@screen_type
class ConversationScreen(Screen):
	"""Single conversation view"""
	conversation_id: str
	
	def __init__(self, session: 'Session', conversation_id: str):
		self.conversation_id = conversation_id
		try:
			conversation = Conversation.load(conversation_id)
		except FileNotFoundError:
			raise ValueError(f"Conversation {conversation_id} does not exist")
		
		super().__init__(
			session=session,
			title=f"Conversation {conversation.short_id}",
			controls=[
				ModalControl(
					id="speak",
					text="Start Speaking",
					keyphrases=["start speaking", "begin speaking"],
					deactivate_phrases=["stop speaking", "end speaking"],
					action=self._handle_speech
				),
				Control(
					id="send",
					text="Send Message",
					keyphrases=["send message"],
					action=self._send_message,
					js_getter_function="getMessageInput",
					js_return_handler="clearMessageInput"
				),
				session.make_back_control()
			]
		)
		self.session.conversation_manager.set_current_conversation(conversation)
		
	def _handle_speech(self) -> None:
		"""Handle speech input from modal control"""
		speak_control = next(c for c in self.controls if c.id == "speak")
		if not isinstance(speak_control, ModalControl):
			return
			
		text = " ".join(w.word for w in speak_control.collected_words)
		if text:
			# TODO: Append to message input
			print(f"Speech input: {text}")
			
	def _send_message(self, message_input:str) -> None:
		"""Send current message"""
		if message_input:
			self.session.conversation_manager.send_message(message_input)

@bp.route(f'/{ConversationScreen.url()}')
def conversation() -> str:
	"""Conversation screen route"""
	session_id = request.args.get('session')
	conversation_id = request.args.get('conversation_id')
	
	session = get_or_create_session(session_id)
	
	# Create conversation screen if needed
	screen = session.app.screen_stack.current
	if not isinstance(screen, ConversationScreen) or screen.conversation_id != conversation_id:
		screen = ConversationScreen(session, conversation_id)
		session.app.screen_stack.push(screen)
	
	return render_template(
		'conversation.html',
		screen=screen,
		session_id=session.id,
		conversation_id=conversation_id
	)

@bp.route(f'/conversation_data', methods=['POST'])
def conversation_data() -> str:
	data = request.get_json()
	conversation_id = data.get('conversation_id')
	
	return jsonify({
		'data':Conversation.load(conversation_id)
	})
