from flask import Flask, render_template, Response
from Alejandro.web.blueprints import blueprints
import json
import queue

from Alejandro.web.voice import core_app, init_app, start_voice_control
from Alejandro.web.events import Event

# Create Flask app
app = Flask(__name__)

# Register blueprints
for bp in blueprints:
    app.register_blueprint(bp)

# Global event queue
event_queue = queue.Queue()


def event_stream() -> str:
    """Server-sent events stream"""
    while True:
        try:
            event = event_queue.get_nowait()
            if isinstance(event, Event):
                yield f"data: {json.dumps(event.__dict__)}\n\n"
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

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
