from typing import List, Optional, Callable
from Alejandro.Core.WordStream import WordStream
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.Screen import Screen
from Alejandro.Core.ScreenStack import ScreenStack
from threading import Thread
from Alejandro.web.events import ControlTriggerEvent, ControlReturnEvent, push_event
import inspect
import time
import queue
import json

class Application:
	"""
	Core application class that processes words from a WordStream
	and manages screens/controls.
	"""
	def __init__(self, word_stream: WordStream, welcome_screen: Screen):
		self.word_stream = word_stream
		self.screen_stack = ScreenStack(welcome_screen)
		self.global_word_handlers: List[Callable[[str], None]] = []
		self._modal_control: Optional[Control] = None
		self.waiting_controls: set[str] = set()
		Thread(target=self.run).start()
	
	def run(self) -> None:
		try:
			print(f"[APP] Application.run() started, waiting for words...", flush=True)
			for word in self.word_stream.words():
				# Notify global handlers
				for handler in self.global_word_handlers:
					handler(word.word)

				# Process through current screen's controls
				screen_name = type(self.screen_stack.current).__name__
				used_control = None

				if self._modal_control:
					result = self._modal_control.validate_word(word)
					if result in (ControlResult.USED, ControlResult.HOLD):
						used_control = self._modal_control.text
						self.call_control(self._modal_control)
					if result == ControlResult.USED:
						self._modal_control = None
				else:
					for control in self.screen_stack.current.controls:
						result = control.validate_word(word)
						if result == ControlResult.HOLD:
							self._modal_control = control
						if result in (ControlResult.USED, ControlResult.HOLD):
							used_control = control.text
							self.call_control(control)
							break

				# Consolidated logging: only log control if it was used
				if used_control:
					print(f"[APP] Processed '{word.word}' on {screen_name} - {used_control}: USED", flush=True)
				else:
					print(f"[APP] Processed '{word.word}' on {screen_name}", flush=True)

				# Block if waiting for controls
				while self.waiting_controls:
					time.sleep(0.01)
		except Exception as e:
			print(f"Processing word stream failed with exception: {e}")
	
	def call_control(self, control: Control) -> None:
		screen = self.screen_stack.current
		session = screen.session
		if control.js_getter_function:
			self.waiting_controls.add(control.id)
			push_event(ControlTriggerEvent(session_id=session.id, control_id=control.id))
		elif control.action:
			return_type = inspect.signature(control.underlying_action).return_annotation
			control_arg_name = control.get_action_control_arg()
			if control_arg_name:
				result = control.action(control)
			else:
				result = control.action()
			if control.js_return_handler and (result is not None or return_type is not inspect._empty):
				push_event(ControlReturnEvent(session_id=session.id, control_id=control.id, return_value=json.dumps(result)))
		elif control.js_return_handler:
			push_event(ControlReturnEvent(session_id=session.id, control_id=control.id, return_value=json.dumps({})))
	
	def notify_control_complete(self, control_id: str):
		self.waiting_controls.discard(control_id)
	
	def close(self):
		self.word_stream.close()
		
	def add_global_word_handler(self, handler: Callable[[str], None]) -> None:
		"""Add a handler that receives all words regardless of controls"""
		self.global_word_handlers.append(handler)
