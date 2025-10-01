from flask import Blueprint, jsonify, Response, request
from Alejandro.web.session import get_or_create_session, Screen
import json

bp = Blueprint('controls', __name__)

@bp.route('/control', methods=['POST'])
def trigger_control() -> Response:
    '''
    Triggers a control from the client.
    '''
    data = request.get_json()
    session_id = data.get('session_id')
    control_id = data.get('control_id')
    url = data.get('window_path')[1:]
    extra_url_params = data.get('extra_url_params', {})
    
    function_arguments = data.get('function_arguments', {})
    from_python = data.get('from_python', False)
    
    screen_type = Screen.types[url]
    session = get_or_create_session(session_id)
    current_screen = session.current_or_get(screen_type, **extra_url_params)
    
    response_data = {
        "screen": type(session.app.screen_stack.current).url()
    }
    
    for control in current_screen.controls:
        if control.id == control_id:
            if control.action:
                result = control.action(**function_arguments)
                if result is not None:
                    response_data["return_value"] = json.dumps(result)
                if from_python:
                    session.app.notify_control_complete(control_id)
            return jsonify(response_data)
       
    return jsonify({"error": "Control not found"}), 404
