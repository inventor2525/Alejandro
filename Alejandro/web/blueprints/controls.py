from flask import Blueprint, jsonify, Response, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('controls', __name__)

@bp.route('/control', methods=['POST'])
def trigger_control() -> Response:
    """Handle control activation"""
    data = request.get_json()
    control_id = data.get('control_id')
    session_id = data.get('session_id')
    
    if not control_id or not session_id:
        return jsonify({"error": "Missing control_id or session_id"}), 400
        
    session = get_or_create_session(session_id)
    current_screen = session.screen_stack.current
    
    for control in current_screen.controls:
        if control.id == control_id:
            if control.action:
                control.action()
            return jsonify({})
            
    return jsonify({"error": "Control not found"}), 404
