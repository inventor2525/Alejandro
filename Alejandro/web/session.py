import uuid
from typing import Dict, Optional, Type, Union, TypeVar, Tuple, List, Callable
from weakref import ref, ReferenceType
from datetime import datetime, timedelta
from Alejandro.Core.Control import Control
from Alejandro.Core.Application import Application 
from Alejandro.Core.ScreenStack import ScreenStack
from Alejandro.Core.WhisperLiveKitWordStream import WhisperLiveKitWordStream
from Alejandro.Core.Assistant import Assistant,Conversation
from Alejandro.web.events import NavigationEvent, ConversationUpdateEvent, push_event
from Alejandro.Core.Screen import Screen
from Alejandro.web.terminal import Terminal
from functools import partial
import os

sessions: Dict[str, 'Session'] = {}

class Session:
	"""Manages application state for a browser session"""
	def __init__(self, welcome_screen_type: Type[Screen], id:Optional[str]=None):
		if not id:
			id = str(uuid.uuid4())
		self.id = id
		self.last_active = datetime.now()
		self._screens: Dict[Type[Screen], Screen] = {}
		self.terminals: Dict[str, 'Terminal'] = {}
		self.current_terminal_index = 0
		
		self.conversation_manager = Assistant(self.id)
		def _push_update(session_id:str, conversation:Conversation):
			"""Push conversation update."""
			push_event(ConversationUpdateEvent(
				session_id=session_id,
				conversation_id=conversation.id,
				data=conversation.to_dict()
			))
		self.conversation_manager.screen_should_update.connect(_push_update)
		
		# Create session-specific word stream and app
		self.word_stream = WhisperLiveKitWordStream(
			os.path.expanduser("~/Documents/Alejandro/Recordings"),
			session_id=self.id
		)
		welcome_screen = self.get_screen(welcome_screen_type)
		self.app = Application(self.word_stream, welcome_screen)
		
	def get_screen(self, screen_type: Type[Screen], **kwargs) -> Screen:
		"""Get existing screen instance or create new one"""
		if screen_type not in self._screens:
			screen = screen_type(session=self, **kwargs)
			self._screens[screen_type] = screen
		return self._screens[screen_type]
		
	def navigate(self, target_screen: Union[Type[Screen], Screen]) -> None:
		"""Navigate to a screen"""
		if isinstance(target_screen, type):
			screen = self.get_screen(target_screen)
		else:
			screen = target_screen
			
		self.app.screen_stack.push(screen)
		from Alejandro.web.blueprints.conversation import ConversationScreen
		print(f"Pushing navigation event for screen: {type(screen).__name__} with session: {self.id}")
		extra_url_params = {}
		if isinstance(screen, ConversationScreen):
			extra_url_params['conversation_id'] = screen.conversation_id
		push_event(NavigationEvent(
			screen=type(screen),
			session_id=self.id,
			extra_url_params=extra_url_params
		))
	
	def navigator(self, target_screen: Union[Type[Screen], Screen]) -> Callable[[],None]:
		'''Returns a function that will navigate to the passed screen when called'''
		return partial(self.navigate, target_screen)
	
	def go_back(self) -> None:
		"""Pop current screen and return to previous"""
		if self.app.screen_stack.pop():
			current = self.app.screen_stack.current
			push_event(NavigationEvent(
				screen=type(current),
				session_id=self.id
			))
			
	def go_forward(self) -> None:
		"""Navigate forward in history if possible"""
		if self.app.screen_stack.forward():
			current = self.app.screen_stack.current
			push_event(NavigationEvent(
				screen=type(current),
				session_id=self.id
			))
			
	def make_back_control(self) -> Control:
		"""Create a back navigation control"""
		return Control(
			id="back",
			text="Back",
			keyphrases=["back", "go back", "return"],
			action=lambda s=self: s.go_back() if s else None
		)
	
	def close(self):
		'''Closes this session.'''
		for terminal in self.terminals.values():
			terminal.close()
	
	def current_or_get(self, screen_type:Type[Screen], **kwargs) -> Screen:
		if isinstance(self.app.screen_stack.current, screen_type):
			return self.app.screen_stack.current
		screen = self.get_screen(screen_type, **kwargs)
		self.app.screen_stack.push(screen)
		return screen

from datetime import datetime, timedelta

def cleanup_sessions() -> None:
	"""Remove inactive sessions older than 1 hour"""
	now = datetime.now()
	to_remove:List[Tuple[str, Session]] = []
	for session_id, session in sessions.items():
		if now - session.last_active > timedelta(hours=1):
			to_remove.append((session_id,session))
			
	for session_id,session in to_remove:
		session.close()
		del sessions[session_id]

def get_or_create_session(session_id: Optional[str] = None) -> Session:
	"""Get existing session or create new one"""    
	if session_id and session_id in sessions:
		sessions[session_id].last_active = datetime.now()
		return sessions[session_id]
	cleanup_sessions()
	
	from Alejandro.web.blueprints.welcome import WelcomeScreen
	session = Session(WelcomeScreen, id=session_id)
	sessions[session.id] = session
	
	return session
