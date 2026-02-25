import sys
import os
from datetime import datetime

# Parse --backend before any other imports so session.py picks up the env var.
# Usage: python app.py --backend wlk     (default, WhisperLiveKit)
#        python app.py --backend voxtral  (Voxtral via vLLM)
#
# vLLM endpoint is configured via env vars:
#   VOXTRAL_HOST  (default: localhost)
#   VOXTRAL_PORT  (default: 8000)
#   VOXTRAL_MODEL (default: mistralai/Voxtral-Mini-4B-Realtime-2602)
_backend = 'wlk'
for _i, _arg in enumerate(sys.argv[1:], 1):
	if _arg == '--backend' and _i + 1 < len(sys.argv):
		_backend = sys.argv[_i + 1]
	elif _arg.startswith('--backend='):
		_backend = _arg.split('=', 1)[1]
os.environ['ALEJANDRO_BACKEND'] = _backend

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
from Alejandro.web.events import events_bp

if _backend == 'voxtral':
	from Alejandro.Core.VoxtralWordStream import VoxtralWordStream as _StreamImpl
	print(f"[APP] Backend: Voxtral (vLLM at {os.environ.get('VOXTRAL_HOST','localhost')}:{os.environ.get('VOXTRAL_PORT','8000')})")
else:
	from Alejandro.Core.WhisperLiveKitWordStream import WhisperLiveKitWordStream as _StreamImpl
	print("[APP] Backend: WhisperLiveKit (localagreement)")

# Create Flask app
app = Flask(__name__)

# Register blueprints
for bp in blueprints:
	app.register_blueprint(bp)
app.register_blueprint(events_bp)
_StreamImpl.init_app(app)

if __name__ == '__main__':
	_StreamImpl.socketio.run(
		app,
		host='0.0.0.0',
		port=5000,
		debug=True,
		allow_unsafe_werkzeug=True,
		ssl_context='adhoc'
	)