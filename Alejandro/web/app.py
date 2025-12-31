import sys
import os
from datetime import datetime

# Set up global logging to file AND console
class TeeOutput:
	"""Redirect print statements to both console and log file"""
	def __init__(self, file_path, original_stream):
		self.file = open(file_path, 'a', buffering=1)  # Line buffered
		self.original = original_stream
		self.file.write(f"\n{'='*80}\n")
		self.file.write(f"[{datetime.now().isoformat()}] App started\n")
		self.file.write(f"{'='*80}\n")

	def write(self, data):
		self.original.write(data)
		self.original.flush()
		self.file.write(data)
		self.file.flush()

	def flush(self):
		self.original.flush()
		self.file.flush()

	def close(self):
		self.file.close()

# Redirect stdout and stderr to file + console
log_file = os.path.expanduser("~/alejandro_app.log")
sys.stdout = TeeOutput(log_file, sys.stdout)
sys.stderr = TeeOutput(log_file, sys.stderr)

print(f"[APP] Global logging enabled: {log_file}")

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
	app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)