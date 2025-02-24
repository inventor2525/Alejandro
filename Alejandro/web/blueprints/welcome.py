from flask import Blueprint, render_template
from Alejandro.web.voice import core_app

bp = Blueprint('welcome', __name__)

@bp.route('/welcome')
def welcome() -> str:
    """Welcome screen route"""
    return render_template(
        'base.html',
        screen=core_app.screen_stack.current,
        **core_app.screen_stack.current.get_template_data()
    )
