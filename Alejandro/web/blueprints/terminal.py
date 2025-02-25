from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control

bp = Blueprint('terminal', __name__)

class TerminalScreen(Screen):
    """Terminal emulator screen"""
    def __init__(self, session: 'Session'):
        super().__init__(
            session=session,
            title="Terminal",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=self: s.session().go_back()
            )]
        )

@bp.route('/terminal')
def terminal() -> str:
    """Terminal screen route"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
    
    session = get_or_create_session(session_id)
    screen = session.screen_stack.current
    
    return render_template(
        'base.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
