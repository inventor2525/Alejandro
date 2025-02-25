from flask import Blueprint, jsonify, Response, request
from Alejandro.web.session import get_or_create_session

bp = Blueprint('controls', __name__)

@bp.route('/control', methods=['POST'])
def trigger_control() -> Response:
    """Handle control activation"""
    print("\n=== Control Trigger Start ===")
    data = request.get_json()
    control_id = data.get('control_id')
    session_id = data.get('session_id')
    print(f"Received control request - control_id: {control_id}, session_id: {session_id}")
    
    if not control_id or not session_id:
        print("Error: Missing control_id or session_id")
        return jsonify({"error": "Missing control_id or session_id"}), 400
        
    session = get_or_create_session(session_id)
    print(f"Got/created session for control with id: {session.id}")
    current_screen = session.screen_stack.current
    print(f"Current screen: {current_screen.__class__.__name__}")
    print(f"Available controls: {[c.id for c in current_screen.controls]}")
    
    for control in current_screen.controls:
        if control.id == control_id:
            print(f"Found matching control: {control_id}")
            if control.action:
                print("Executing control action...")
                control.action()
                print("Action completed")
            return jsonify({})
    
    print(f"Error: Control {control_id} not found")        
    return jsonify({"error": "Control not found"}), 404
