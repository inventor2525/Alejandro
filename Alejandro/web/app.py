from flask import Flask, render_template, Response, request
from Alejandro.web.blueprints import blueprints
from Alejandro.Core.WhisperLiveKitWordStream import WhisperLiveKitWordStream
from Alejandro.web.events import events_bp

# Create Flask app
app = Flask(__name__)

# Register blueprints
for bp in blueprints:
	app.register_blueprint(bp)
app.register_blueprint(events_bp)
WhisperLiveKitWordStream.init_app(app)

if __name__ == '__main__':
	app.run(debug=True, threaded=True)