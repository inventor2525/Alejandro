from flask import Blueprint, render_template
from Alejandro.web.voice import core_app, init_app
from Alejandro.web.screens import WelcomeScreen

bp = Blueprint('default_screen', __name__)

@bp.route('/')
def index() -> str:
    """Default screen route"""
    if core_app is None:
        init_app(WelcomeScreen())
    
    return render_template(
        'base.html',
        screen=core_app.screen_stack.current,
        **core_app.screen_stack.current.get_template_data()
    )
