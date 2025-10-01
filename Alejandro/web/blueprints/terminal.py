from flask import Blueprint, render_template, request, jsonify
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type
from Alejandro.Core.Control import Control
from Alejandro.web.terminal import Terminal
from Alejandro.web.events import TerminalScreenEvent, push_event
import time

bp = Blueprint('terminal', __name__)

@screen_type
class TerminalScreen(Screen):
	"""Terminal emulator screen"""
	def __init__(self, session: 'Session'):
		# Get terminal info
		terminal_names = list(session.terminals.keys())
		current_terminal = terminal_names[session.current_terminal_index] if terminal_names and session.terminals else "none"
		
		super().__init__(
			session=session,
			title=f"Terminal - {current_terminal}",
			controls=[
				Control(
					id="new",
					text="New Terminal",
					keyphrases=["new terminal", "create terminal"],
					action=lambda s=self: s._create_new_terminal()
				),
				Control(
					id="next",
					text="Next Terminal",
					keyphrases=["next terminal"],
					action=lambda s=self: s._next_terminal()
				),
				Control(
					id="prev",
					text="Previous Terminal",
					keyphrases=["previous terminal", "prev terminal"],
					action=lambda s=self: s._prev_terminal()
				),
				session.make_back_control()
			]
		)
	
	def _create_new_terminal(self) -> None:
		"""Create a new terminal"""
		session = self.session
		terminal_id = f"terminal_{len(session.terminals) + 1}"
		# Create the new terminal
		new_terminal = Terminal(terminal_id, session.id)
		session.terminals[terminal_id] = new_terminal
		session.current_terminal_index = len(session.terminals) - 1
		self.title = f"Terminal - {terminal_id}"
		
		# Give the terminal a moment to initialize
		time.sleep(0.2)
		
		# Send a terminal switch event and replay the buffer
		new_terminal.replay_buffer()
	
	def _next_terminal(self) -> None:
		"""Switch to next terminal"""
		session = self.session
		terminal_names = list(session.terminals.keys())
		if terminal_names:
			session.current_terminal_index = (session.current_terminal_index + 1) % len(terminal_names)
			current_terminal = terminal_names[session.current_terminal_index]
			self.title = f"Terminal - {current_terminal}"
			
			# Get the terminal instance and replay its buffer
			terminal = session.terminals[current_terminal]
			# Replay the full buffer to restore all previous output
			terminal.replay_buffer()
	
	def _prev_terminal(self) -> None:
		"""Switch to previous terminal"""
		session = self.session
		terminal_names = list(session.terminals.keys())
		if terminal_names:
			session.current_terminal_index = (session.current_terminal_index - 1) % len(terminal_names)
			current_terminal = terminal_names[session.current_terminal_index]
			self.title = f"Terminal - {current_terminal}"
			
			# Get the terminal instance and replay its buffer
			terminal = session.terminals[current_terminal]
			# Replay the full buffer to restore all previous output
			terminal.replay_buffer()
			
	
	def get_template_data(self) -> dict:
		"""Get template data for rendering"""
		session = self.session
		terminal_names = list(session.terminals.keys())
		current_terminal = terminal_names[session.current_terminal_index] if terminal_names else None
		
		return {
			"terminal_id": current_terminal
		}

@bp.route(f'/{TerminalScreen.url()}')
def terminal() -> str:
	"""Terminal screen route"""
	session_id = request.args.get('session')
	terminal_id = request.args.get('terminal_id')
	
	session = get_or_create_session(session_id)
	
	# Check if we already have a terminal screen in the stack
	current_screen = session.current_or_get(TerminalScreen)
	if isinstance(current_screen, TerminalScreen):
		screen = current_screen
	else:
		# Create terminal screen and push it to the stack
		screen = TerminalScreen(session)
		session.app.screen_stack.push(screen)
	
	# Make sure terminal exists
	if not session.terminals:
		print("Creating terminal for session in route handler")
		session.terminals["main"] = Terminal("main", session.id)
		session.current_terminal_index = 0
	
	# If terminal_id is specified, switch to it
	if terminal_id and terminal_id in session.terminals:
		terminal_names = list(session.terminals.keys())
		session.current_terminal_index = terminal_names.index(terminal_id)
		screen.title = f"Terminal - {terminal_id}"
		
		# Get the terminal instance
		terminal = session.terminals[terminal_id]
		# Replay the full terminal buffer
		terminal.replay_buffer()
	
	# Get template data
	template_data = screen.get_template_data()
	print(f"Rendering terminal with data: {template_data}")
	
	return render_template(
		'terminal.html',
		screen=screen,
		session_id=session.id,
		body_class="terminal-page",
		**template_data
	)

@bp.route('/terminal/input', methods=['POST'])
def terminal_input():
	"""Handle terminal input"""
	data = request.get_json()
	session_id = data.get('session_id')
	terminal_id = data.get('terminal_id')
	input_text = data.get('input')
	
	session = get_or_create_session(session_id)
	
	# Create terminal if it doesn't exist
	if not session.terminals:
		print(f"Creating terminal '{terminal_id}' for session during input")
		session.terminals[terminal_id] = Terminal(terminal_id, session.id)
		session.current_terminal_index = 0
	
	if terminal_id in session.terminals:
		session.terminals[terminal_id].send_input(input_text)
		return jsonify({"status": "ok"})
	else:
		# Create the specific terminal if it doesn't exist
		print(f"Creating requested terminal '{terminal_id}'")
		session.terminals[terminal_id] = Terminal(terminal_id, session.id)
		session.terminals[terminal_id].send_input(input_text)
		return jsonify({"status": "ok", "created": True})

@bp.route('/terminal/resize', methods=['POST'])
def terminal_resize():
	"""Handle terminal resize"""
	data = request.get_json()
	session_id = data.get('session_id')
	terminal_id = data.get('terminal_id')
	cols = data.get('cols')
	rows = data.get('rows')
	
	session = get_or_create_session(session_id)
	
	if terminal_id in session.terminals:
		session.terminals[terminal_id].resize(cols, rows)
		return jsonify({"status": "ok"})
	else:
		return jsonify({"error": "Terminal not found"}), 404
