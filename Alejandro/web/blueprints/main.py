from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control

bp = Blueprint('main', __name__)

class MainScreen(Screen):
    """Main menu screen"""
    def __init__(self, session: 'Session'):
        from Alejandro.web.blueprints.conversations import ConversationsScreen
        from Alejandro.web.blueprints.terminal import TerminalScreen
        super().__init__(
            session=session,
            title="Main Menu",
            controls=[
                Control(
                    id="conversations",
                    text="Conversations",
                    keyphrases=["conversations", "show conversations"],
                    action=lambda s=self: s.session().navigate(ConversationsScreen)
                ),
                Control(
                    id="terminal", 
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda s=self: s.session().navigate(TerminalScreen)
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=self: s.session().go_back()
                )
            ]
        )

@bp.route('/<screen_name>')
def show_screen(screen_name: str) -> str:
    """Generic screen route handler"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
        
    session = get_or_create_session(session_id)
    screen = session.screen_stack.current
    print(f"Loading {screen_name} for session {session_id}")
    print(f"Current screen type: {type(screen).__name__}")
    print(f"Screen stack contents: {[type(s).__name__ for s in session.screen_stack._stack]}")
    return render_template(
        'base.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
