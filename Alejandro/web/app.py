from flask import Flask, render_template, Response, request
from typing import Iterator
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

def event_stream(session_id: str) -> Iterator[str]:
    """Server-sent events stream"""
    print(f"Starting event stream for session: {session_id}")
    while True:
        try:
            event = event_queue.get_nowait()
            print(f"Got event from queue: {event.__class__.__name__}")
            if isinstance(event, Event):
                print(f"Event session: {event.session_id}, Current session: {session_id}")
                if event.session_id == session_id:
                    event_json = json.dumps(event.to_json())
                    print(f"Sending event to client: {event_json}")
                    yield f"data: {event_json}\n\n"
                else:
                    print("Event session ID mismatch - skipping")
            else:
                print(f"Non-Event object in queue: {type(event)}")
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
