from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('screens', __name__)

@bp.route('/<screen_name>')
def show_screen(screen_name: str):
    """Handle screen routes"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
        
    session = get_or_create_session(session_id)
    screen = session.screen_stack.current
    
    # Get screen-specific template if it exists, fall back to base.html
    template = f"{screen_name}.html"
    try:
        render_template(template)  # Test if template exists
        return render_template(template, screen=screen, session_id=session_id)
    except:
        return render_template('base.html', screen=screen, session_id=session_id)
