from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control

bp = Blueprint('welcome', __name__)

class WelcomeScreen(Screen):
    """Initial welcome screen"""
    def __init__(self, session: 'Session'):
        from Alejandro.web.blueprints.main import MainScreen
        super().__init__(
            session=session,
            title="Welcome",
            controls=[
                Control(
                    id="activate",
                    text="Hey Alejandro",
                    keyphrases=["hey alejandro", "hello alejandro"],
                    action=lambda s=self: s.session().navigate(MainScreen)
                )
            ]
        )

@bp.route('/')
@bp.route('/welcome')
def welcome() -> str:
    """Welcome screen route"""
    session_id = request.args.get('session')
    
    session = get_or_create_session(session_id)
    screen = session.screen_stack.current
    
    return render_template(
        'base.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
