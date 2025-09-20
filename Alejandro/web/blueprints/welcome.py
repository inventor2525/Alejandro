from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type
from Alejandro.Core.Control import Control

bp = Blueprint('welcome', __name__)

@screen_type
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
                    action=lambda s=self: s.session.navigate(MainScreen)
                )
            ]
        )
Screen.types[''] = WelcomeScreen

@bp.route('/')
@bp.route(f'/{WelcomeScreen.url()}')
def welcome() -> str:
    """Welcome screen route"""
    session_id = request.args.get('session')
    
    session = get_or_create_session(session_id)
    screen = session.current_or_get(WelcomeScreen)
    
    return render_template(
        'base.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
