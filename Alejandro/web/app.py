from flask import Flask, render_template, jsonify, Response, request
from Alejandro.web.blueprints import blueprints
from typing import Dict, Any
import json
import queue
import threading

from Alejandro.Core.application import Application
from Alejandro.Core.string_word_stream import StringWordStream
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import ControlResult

# Create Flask app
app = Flask(__name__)

# Register blueprints
for bp in blueprints:
    app.register_blueprint(bp)

from Alejandro.web.events import Event, TranscriptionEvent, NavigationEvent, ButtonClickEvent

# Global event queue
event_queue = queue.Queue()

# Global app instance 
core_app = None
word_stream = None

def init_app(welcome_screen: Screen) -> None:
    """Initialize the core application"""
    global core_app, word_stream
    if core_app is None:
        from Alejandro.Core.test_word_stream import TestWordStream
        word_stream = TestWordStream()
        core_app = Application(word_stream, welcome_screen)

@app.route('/')
@app.route('/<path:screen_id>')
def index(screen_id: str = None) -> str:
    """Render the current screen"""
    if screen_id == 'favicon.ico':
        return '', 204
        
    # Initialize if needed
    if core_app is None:
        from Alejandro.web.screens import WelcomeScreen
        init_app(WelcomeScreen())
    
    return render_template(
        'base.html',
        screen=core_app.screen_stack.current,
        **core_app.screen_stack.current.get_template_data()
    )

@app.route('/control', methods=['POST'])
def trigger_control() -> Response:
    """Handle control activation"""
    data = request.get_json()
    control_id = data.get('control_id')
    
    if not control_id:
        return jsonify({"error": "No control ID provided"}), 400
        
    current_screen = core_app.screen_stack.current
    
    for control in current_screen.controls:
        if control.id == control_id:
            if control.action:
                control.action()
            return jsonify({})
            
    return jsonify({"error": "Control not found"}), 404

def event_stream() -> str:
    """Server-sent events stream"""
    while True:
        # Check transcription queue
        try:
            transcription = transcription_queue.get_nowait()
            yield f"data: {json.dumps({'text': transcription})}\n\n"
        except queue.Empty:
            pass
            
        # Check action queue  
        try:
            action = action_queue.get_nowait()
            yield f"data: {json.dumps(action)}\n\n"
        except queue.Empty:
            pass
            
        # Keep-alive
        yield ": keepalive\n\n"

@app.route('/stream')
def stream() -> Response:
    """SSE endpoint"""
    return Response(
        event_stream(),
        mimetype='text/event-stream'
    )

def voice_control_thread() -> None:
    """Background thread for voice processing"""
    try:
        core_app.run()
    except Exception as e:
        print(f"Voice control error: {e}")

def start_voice_control() -> None:
    """Start voice control in background thread"""
    thread = threading.Thread(target=voice_control_thread)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
