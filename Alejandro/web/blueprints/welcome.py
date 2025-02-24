from flask import Blueprint, render_template, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('welcome', __name__)

@bp.route('/welcome')
def welcome() -> str:
    """Welcome screen route"""
    session_id = request.args.get('session')
    session = get_or_create_session(session_id)
    
    return render_template(
        'base.html',
        screen=session.screen_stack.current,
        session_id=session.id,
        **session.screen_stack.current.get_template_data()
    )
