from flask import Blueprint, render_template, request
from typing import Dict, Any, List
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type
from Alejandro.Core.Control import Control
from Alejandro.Core.ModelControl import ModalControl
from Alejandro.Models.Conversation import Conversation, Message, Roles
import os
import uuid

bp = Blueprint('conversations', __name__)

@screen_type
class ConversationsScreen(Screen):
	"""List of conversations"""
	def __init__(self, session: 'Session'):
		super().__init__(
			session=session,
			title="Conversations",
			controls=[
				ModalControl(
					id="select",
					text="Select Conversation",
					keyphrases=["select conversation", "choose conversation"],
					deactivate_phrases=["end selection"],
					action=lambda s=self: self._handle_selection()
				),
				Control(
					id="new",
					text="New Conversation",
					keyphrases=["new conversation", "create conversation"],
					action=lambda s=self: self._create_new_conversation()
				),
				session.make_back_control()
			]
		)
		
	def _create_new_conversation(self) -> None:
		from Alejandro.web.blueprints.conversation import ConversationScreen
		conv = Conversation()
		conv.save()
		screen = ConversationScreen(self.session, conv.id)
		self.session.navigate(screen)
		
	def _handle_selection(self) -> None:
		"""Handle conversation selection from modal control"""
		# Get the selected text from modal control
		select_control = next(c for c in self.controls if c.id == "select")
		if not isinstance(select_control, ModalControl):
			return
			
		# Join collected words into selection text
		selection = " ".join(w.word for w in select_control.collected_words)
		
		# Find best matching conversation
		conversations = self.get_conversations()
		for conv in conversations:
			if selection.lower() in conv["name"].lower():
				# TODO: Navigate to conversation
				print(f"Selected conversation: {conv['name']}")
				break
	
	def get_conversations(self) -> List[Dict[str, str]]:
		"""Get list of conversations"""
		convs = []
		files = [f for f in os.listdir(Conversation.ROOT_DIRECTORY) if f.endswith('.json')]
				
		for file in files:
			conv_id = os.path.splitext(file)[0]
			conv = Conversation.load(conv_id)
			convs.append({
				"id": conv.id,
				"name": conv.name,
				"description": conv.description
			})
		return convs
		
	def get_template_data(self) -> Dict[str, Any]:
		return {
			"conversations": self.get_conversations()
		}

@bp.route(f'/{ConversationsScreen.url()}')
def conversations() -> str:
	"""Conversations screen route"""
	session_id = request.args.get('session')
	
	session = get_or_create_session(session_id)
	screen = session.current_or_get(ConversationsScreen)
	
	template_data = screen.get_template_data()
	print(f"Rendering conversations with data: {template_data}")
	
	return render_template(
		'conversation_list.html',
		screen=screen,
		session_id=session.id,
		**template_data
	)
