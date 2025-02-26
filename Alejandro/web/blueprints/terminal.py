from flask import Blueprint, render_template, request, jsonify
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.web.terminal import Terminal

bp = Blueprint('terminal', __name__)

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
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=self: s.session().go_back()
                )
            ]
        )
    
    def _create_new_terminal(self) -> None:
        """Create a new terminal"""
        session = self.session()
        terminal_id = f"terminal_{len(session.terminals) + 1}"
        session.terminals[terminal_id] = Terminal(terminal_id, session.id)
        session.current_terminal_index = len(session.terminals) - 1
        self.title = f"Terminal - {terminal_id}"
    
    def _next_terminal(self) -> None:
        """Switch to next terminal"""
        session = self.session()
        terminal_names = list(session.terminals.keys())
        if terminal_names:
            session.current_terminal_index = (session.current_terminal_index + 1) % len(terminal_names)
            current_terminal = terminal_names[session.current_terminal_index]
            self.title = f"Terminal - {current_terminal}"
    
    def _prev_terminal(self) -> None:
        """Switch to previous terminal"""
        session = self.session()
        terminal_names = list(session.terminals.keys())
        if terminal_names:
            session.current_terminal_index = (session.current_terminal_index - 1) % len(terminal_names)
            current_terminal = terminal_names[session.current_terminal_index]
            self.title = f"Terminal - {current_terminal}"
    
    def get_template_data(self) -> dict:
        """Get template data for rendering"""
        session = self.session()
        terminal_names = list(session.terminals.keys())
        current_terminal = terminal_names[session.current_terminal_index] if terminal_names else None
        
        return {
            "terminal_id": current_terminal,
            "terminal_names": terminal_names,
            "current_index": session.current_terminal_index
        }

@bp.route(f'/{TerminalScreen.url()}')
def terminal() -> str:
    """Terminal screen route"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
    
    session = get_or_create_session(session_id)
    
    # Create terminal screen
    screen = TerminalScreen(session)
    
    # Make sure terminal exists
    if not session.terminals:
        print("Creating terminal for session in route handler")
        session.terminals["main"] = Terminal("main", session.id)
        session.current_terminal_index = 0
        session.terminals["main"]._send_screen_update()
    
    # Get template data
    template_data = screen.get_template_data()
    print(f"Rendering terminal with data: {template_data}")
    
    return render_template(
        'terminal.html',
        screen=screen,
        session_id=session.id,
        **template_data
    )

@bp.route('/terminal/input', methods=['POST'])
def terminal_input():
    """Handle terminal input"""
    data = request.get_json()
    session_id = data.get('session_id')
    terminal_id = data.get('terminal_id')
    input_text = data.get('input')
    
    if not all([session_id, terminal_id, input_text]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    session = get_or_create_session(session_id)
    
    # Create terminal if it doesn't exist
    if not session.terminals:
        print(f"Creating terminal '{terminal_id}' for session during input")
        session.terminals[terminal_id] = Terminal(terminal_id, session.id)
        session.current_terminal_index = 0
        session.terminals[terminal_id]._send_screen_update()
    
    if terminal_id in session.terminals:
        session.terminals[terminal_id].send_input(input_text)
        return jsonify({"status": "ok"})
    else:
        # Create the specific terminal if it doesn't exist
        print(f"Creating requested terminal '{terminal_id}'")
        session.terminals[terminal_id] = Terminal(terminal_id, session.id)
        session.terminals[terminal_id].send_input(input_text)
        return jsonify({"status": "ok", "created": True})
