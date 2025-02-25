from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('welcome', __name__)

@bp.route('/')
@bp.route('/welcomescreen')
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
