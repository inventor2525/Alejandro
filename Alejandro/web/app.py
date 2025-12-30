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

# Pre-load WhisperLiveKit TranscriptionEngine at startup
print("[INIT] Pre-loading WhisperLiveKit TranscriptionEngine...")
WhisperLiveKitWordStream.preload_transcription_engine(
	model="large-v3",
	diarization=True,
	language="en"
)
print("[INIT] TranscriptionEngine pre-loaded successfully")

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)