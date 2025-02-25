from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('main', __name__)

@bp.route('/mainscreen')
def show_main() -> str:
    """Main screen route"""
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
