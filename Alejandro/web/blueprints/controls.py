from flask import Blueprint, jsonify, Response, request
from Alejandro.web.session import get_or_create_session, Screen

bp = Blueprint('controls', __name__)

@bp.route('/control', methods=['POST'])
def trigger_control() -> Response:
    """Handle control activation"""
    data = request.get_json()
    control_id = data.get('control_id')
    session_id = data.get('session_id')
    url = data.get('window_path')[1:]
    screen_type = Screen.types[url]
    
    session = get_or_create_session(session_id)
    current_screen = session.current_or_get(screen_type)
    
    for control in current_screen.controls:
        if control.id == control_id:
            if control.action:
                control.action()
                
                return jsonify({
                    "screen": type(session.app.screen_stack.current).url()
                })
            return jsonify({})
       
    return jsonify({"error": "Control not found"}), 404
