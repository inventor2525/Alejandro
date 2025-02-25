from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('main', __name__)

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
