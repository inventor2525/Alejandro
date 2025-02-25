from flask import Blueprint, render_template, request
from typing import Dict, Any
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control

bp = Blueprint('conversations', __name__)

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self, session: 'Session'):
        super().__init__(
            session=session,
            title="Conversations",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=self: s.session().go_back()
            )]
        )
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "conversations": []  # TODO: Get actual conversations
        }

@bp.route('/conversationsscreen')
def conversations() -> str:
    """Conversations screen route"""
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
