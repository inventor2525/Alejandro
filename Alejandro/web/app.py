from flask import Flask, render_template, jsonify, Response
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

# Global queues for communication
transcription_queue = queue.Queue()
action_queue = queue.Queue()

# Global app instance 
core_app = None
word_stream = None

def init_app(welcome_screen: Screen) -> None:
    """Initialize the core application"""
    global core_app, word_stream
    if core_app is None:
        word_stream = StringWordStream()
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

@app.route('/control/<control_id>', methods=['POST'])
def trigger_control(control_id: str) -> Response:
    """Handle control activation"""
    current_screen = core_app.screen_stack.current
    
    for control in current_screen.controls:
        if control.id == control_id:
            if control.action:
                result = control.action()
                return jsonify({"result": result})
            break
            
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
