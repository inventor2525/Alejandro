from flask import Flask, render_template, Response, request
from Alejandro.web.session import get_or_create_session
from Alejandro.web.blueprints import blueprints
import json
import queue
import time

from Alejandro.web.events import Event, event_queue

# Create Flask app
app = Flask(__name__)

# Register blueprints
for bp in blueprints:
    app.register_blueprint(bp)

def event_stream(session_id: str) -> str:
    """Server-sent events stream"""
    while True:
        try:
            event = event_queue.get_nowait()
            if isinstance(event, Event) and event.session_id == session_id:
                yield f"data: {json.dumps(event.to_json())}\n\n"
        except queue.Empty:
            pass
        
        # Keep-alive
        time.sleep(0.01)
        yield ": keepalive\n\n"

@app.route('/stream')
def stream() -> Response:
    """SSE endpoint"""
    session_id = request.args.get('session')
    if not session_id:
        return Response("No session ID provided", status=400)
        
    get_or_create_session(session_id)  # Validate session exists
    
    return Response(
        event_stream(session_id),
        mimetype='text/event-stream'
    )

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
