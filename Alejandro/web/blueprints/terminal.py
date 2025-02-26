from flask import Blueprint, render_template, request, jsonify
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.web.terminal import Terminal

bp = Blueprint('terminal', __name__)

class TerminalScreen(Screen):
    """Terminal emulator screen"""
    def __init__(self, session: 'Session'):
        # Create default terminal if none exists
        if not session.terminals:
            print("Creating new terminal for session")
            session.terminals["main"] = Terminal("main", session.id)
            session.current_terminal_index = 0
            # Force immediate screen update
            session.terminals["main"]._send_screen_update()
        
        terminal_names = list(session.terminals.keys())
        current_terminal = terminal_names[session.current_terminal_index] if terminal_names else "none"
        
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
    
    # Create terminal screen if needed
    screen = session.screen_stack.current
    if not isinstance(screen, TerminalScreen):
        screen = TerminalScreen(session)
        session.screen_stack.push(screen)
    
    return render_template(
        'terminal.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
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
    if terminal_id in session.terminals:
        session.terminals[terminal_id].send_input(input_text)
        return jsonify({"status": "ok"})
    
    print(f"Terminal not found: {terminal_id}")
    print(f"Available terminals: {list(session.terminals.keys())}")
    return jsonify({"error": "Terminal not found"}), 404
