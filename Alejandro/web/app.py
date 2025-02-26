from flask import Flask, render_template, Response, request
from typing import Iterator
from Alejandro.web.session import get_or_create_session
from Alejandro.web.blueprints import blueprints
import json
import queue
import time

from Alejandro.web.events import Event, TerminalScreenEvent, event_queue

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
            if isinstance(event, Event):
                if event.session_id == session_id:
                    event_json = json.dumps(event.to_json())
                    # Only log minimal info for terminal events
                    if isinstance(event, TerminalScreenEvent):
                        print(f"Sending terminal event to client for terminal: {event.terminal_id}")
                    else:
                        print(f"Sending event to client: {event.__class__.__name__}")
                    yield f"data: {event_json}\n\n"
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
    print(f"\nStream request with session_id: {session_id}")
    if not session_id:
        return Response("No session ID provided", status=400)
        
    session = get_or_create_session(session_id)  # Validate session exists
    print(f"Got/created session with id: {session.id}")
    
    return Response(
        event_stream(session_id),
        mimetype='text/event-stream'
    )

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
