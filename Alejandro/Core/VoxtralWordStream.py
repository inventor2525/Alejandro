"""
VoxtralWordStream: Drop-in replacement for WhisperLiveKitWordStream using
Mistral AI's Voxtral-Mini-4B-Realtime model served via vLLM.

Voxtral uses causal attention trained end-to-end for streaming, so no chunking
is needed. Audio is streamed to vLLM's /v1/realtime WebSocket endpoint and
the model emits transcription tokens in real time.

Protocol (OpenAI Realtime API-compatible):
  Server → Client: session.created
  Client → Server: session.update  (sets model)
  Client → Server: input_audio_buffer.commit  (start of stream)
  Client → Server: input_audio_buffer.append  (repeated PCM16 chunks, base64)
  Server → Client: transcription.delta  (partial tokens)
  Server → Client: transcription.done   (final transcript per utterance)
  Client → Server: input_audio_buffer.commit final=True  (end of stream)

Audio format required by vLLM: PCM16 (s16le), 16kHz, mono, base64-encoded.
Browser sends WebM/Opus, so ffmpeg converts on the fly.

Configuration via environment variables:
  VOXTRAL_HOST  - vLLM host (default: localhost)
  VOXTRAL_PORT  - vLLM port (default: 8000)
  VOXTRAL_MODEL - Model ID  (default: mistralai/Voxtral-Mini-4B-Realtime-2602)

Known vLLM bug (as of Feb 2026): crashes if client disconnects without
sending final commit first. We always send it in _stop_listening.
"""
from typing import Optional, Iterator, Dict, List
from .WordStream import WordStream, WordNode
from flask import Blueprint, jsonify, Response, request, Flask, render_template
from flask_socketio import SocketIO
from io import BufferedWriter
from queue import Queue, Empty
from datetime import datetime
import json
import os
import re
import time
import base64
import threading
import subprocess
import logging
import nltk
import websocket  # websocket-client library

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VLLM_HOST = os.environ.get("VOXTRAL_HOST", "localhost")
VLLM_PORT = int(os.environ.get("VOXTRAL_PORT", "8000"))
VOXTRAL_MODEL = os.environ.get("VOXTRAL_MODEL", "mistralai/Voxtral-Mini-4B-Realtime-2602")

mime_to_ffmpeg_fmt = {
	"audio/webm": "webm",
	"audio/ogg": "ogg",
	"audio/wav": "wav",
	"audio/mpeg": "mp3",
	"audio/aac": "aac",
}

# ---------------------------------------------------------------------------
# Text cleaning (same logic as WhisperLiveKitWordStream)
# ---------------------------------------------------------------------------
def clean_transcription_text(text: str) -> str:
	"""
	Remove Whisper/Voxtral noise annotations before tokenization:
	- [BLANK_AUDIO], [LAUGHTER], etc.  (complete square brackets)
	- (laughing), (laughs), etc.        (complete parentheses)
	- Incomplete opening/closing brackets at any position
	"""
	text = re.sub(r'\[([^\]]*?)\]', ' ', text)
	text = re.sub(r'\(([^\)]*?)\)', ' ', text)
	text = re.sub(r'\[([^\]]*?)$', ' ', text)
	text = re.sub(r'\[([^\]]*?)\s', ' ', text)
	text = re.sub(r'\(([^\)]*?)$', ' ', text)
	text = re.sub(r'\(([^\)]*?)\s', ' ', text)
	text = re.sub(r'([^\[]*?)\]', ' ', text)
	text = re.sub(r'([^\(]*?)\)', ' ', text)
	text = re.sub(r'\s+', ' ', text).strip()
	return text


# ---------------------------------------------------------------------------
# VoxtralWordStream
# ---------------------------------------------------------------------------
class VoxtralWordStream(WordStream):
	bp = Blueprint('VoxtralWordStream', __name__)
	socketio: SocketIO = SocketIO(
		ping_interval=25,
		ping_timeout=60,
		max_http_buffer_size=10000000
	)
	streams: Dict[str, 'VoxtralWordStream'] = {}

	def __init__(
		self,
		save_directory: Optional[str],
		session_id: Optional[str] = None
	):
		self.session_id = session_id
		VoxtralWordStream.streams[session_id] = self

		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)

		# State
		self._running = True
		self.is_recording = False
		self.word_queue: Queue = Queue()

		# Recording file
		self.file_ext = "webm"
		self.current_audio_path: Optional[str] = None
		self.current_audio_file: Optional[BufferedWriter] = None
		self.start_time: Optional[datetime] = None
		self.end_time: Optional[datetime] = None

		self.last_node: Optional[WordNode] = None
		self.word_lock = threading.Lock()

		# ffmpeg subprocess for WebM → PCM16 conversion
		self.ffmpeg_proc: Optional[subprocess.Popen] = None
		self.ffmpeg_reader_thread: Optional[threading.Thread] = None
		self.pcm_queue: Queue = Queue(maxsize=200)

		# WebSocket to vLLM
		self.ws: Optional[websocket.WebSocketApp] = None
		self.ws_thread: Optional[threading.Thread] = None
		self.ws_connected = threading.Event()
		self.ws_ready = threading.Event()  # Set after session.created handshake

		# PCM sender thread
		self.pcm_sender_thread: Optional[threading.Thread] = None

		# Transcription accumulation (delta tokens between done events)
		self.current_delta = ""

	@staticmethod
	def init_app(app: Flask):
		VoxtralWordStream.socketio.init_app(app)
		app.register_blueprint(VoxtralWordStream.bp)

	def words(self) -> Iterator[WordNode]:
		while self._running:
			try:
				yield self.word_queue.get(block=True, timeout=0.5)
			except Empty:
				pass
		return

	def close(self):
		self._stop_listening()
		self._running = False
		if self.session_id in VoxtralWordStream.streams:
			del VoxtralWordStream.streams[self.session_id]

	# ------------------------------------------------------------------
	# Recording lifecycle
	# ------------------------------------------------------------------

	def _start_listening(self, mime_type: str) -> None:
		self.start_time = datetime.now()
		timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")

		self.file_ext = mime_to_ffmpeg_fmt.get(mime_type, "webm")
		self.current_audio_path = os.path.join(
			self.save_directory,
			f"raw_recording_{timestamp}.{self.file_ext}"
		)
		self.current_audio_file = open(self.current_audio_path, "wb")

		# Start ffmpeg: convert incoming WebM/Opus → PCM16 16kHz mono
		ffmpeg_fmt = mime_to_ffmpeg_fmt.get(mime_type, "webm")
		self.ffmpeg_proc = subprocess.Popen(
			[
				"ffmpeg", "-hide_banner", "-loglevel", "error",
				"-f", ffmpeg_fmt,
				"-i", "pipe:0",
				"-ar", "16000",
				"-ac", "1",
				"-f", "s16le",
				"pipe:1",
			],
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.DEVNULL,
		)
		self.ffmpeg_reader_thread = threading.Thread(
			target=self._ffmpeg_reader, daemon=True
		)
		self.ffmpeg_reader_thread.start()

		# Connect to vLLM WebSocket
		self.ws_connected.clear()
		self.ws_ready.clear()
		self.current_delta = ""
		ws_url = f"ws://{VLLM_HOST}:{VLLM_PORT}/v1/realtime"
		self.ws = websocket.WebSocketApp(
			ws_url,
			on_open=self._on_ws_open,
			on_message=self._on_ws_message,
			on_error=self._on_ws_error,
			on_close=self._on_ws_close,
		)
		self.ws_thread = threading.Thread(
			target=self.ws.run_forever, daemon=True
		)
		self.ws_thread.start()

		if not self.ws_ready.wait(timeout=10.0):
			print(f"[VOXTRAL] Warning: could not connect to vLLM at {ws_url} within 10s")

		self.is_recording = True

		# Start PCM sender (drains pcm_queue → WebSocket)
		self.pcm_sender_thread = threading.Thread(
			target=self._pcm_sender, daemon=True
		)
		self.pcm_sender_thread.start()

	def _stop_listening(self) -> None:
		self.end_time = datetime.now()
		self.is_recording = False

		if self.current_audio_file:
			self.current_audio_file.close()

		# Close ffmpeg stdin → signals end of input → reader thread exits
		if self.ffmpeg_proc and self.ffmpeg_proc.stdin:
			try:
				self.ffmpeg_proc.stdin.close()
			except Exception:
				pass

		# Wait for PCM sender to drain remaining audio
		if self.pcm_sender_thread and self.pcm_sender_thread.is_alive():
			self.pcm_sender_thread.join(timeout=5.0)

		# Send graceful final commit (vLLM crashes without this)
		if self.ws:
			try:
				self.ws.send(json.dumps({
					"type": "input_audio_buffer.commit",
					"final": True
				}))
				time.sleep(0.5)  # Give vLLM a moment to process
			except Exception:
				pass
			try:
				self.ws.close()
			except Exception:
				pass

		if self.ws_thread and self.ws_thread.is_alive():
			self.ws_thread.join(timeout=3.0)

		# Rename recording
		if self.current_audio_path and os.path.exists(self.current_audio_path):
			start_str = self.start_time.strftime("%Y%m%d_%H%M%S")
			end_str = self.end_time.strftime("%Y%m%d_%H%M%S")
			new_path = os.path.join(
				self.save_directory,
				f"recording_{start_str}__{end_str}.{self.file_ext}"
			)
			os.rename(self.current_audio_path, new_path)

	def _handle_audio_chunk(self, data: bytes) -> None:
		# Write to disk
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		# Pipe to ffmpeg for PCM16 conversion
		if self.is_recording and self.ffmpeg_proc and self.ffmpeg_proc.stdin:
			try:
				self.ffmpeg_proc.stdin.write(data)
				self.ffmpeg_proc.stdin.flush()
			except Exception:
				pass

	# ------------------------------------------------------------------
	# Audio conversion thread
	# ------------------------------------------------------------------

	def _ffmpeg_reader(self) -> None:
		"""Read PCM16 chunks from ffmpeg stdout and push to pcm_queue."""
		CHUNK_BYTES = 3200  # 100ms at 16kHz mono PCM16 (16000 * 2 * 0.1)
		try:
			while True:
				chunk = self.ffmpeg_proc.stdout.read(CHUNK_BYTES)
				if not chunk:
					break
				try:
					self.pcm_queue.put(chunk, timeout=2.0)
				except Exception:
					pass
		except Exception as e:
			print(f"[VOXTRAL] ffmpeg reader error: {e}")
		finally:
			# Sentinel: tell pcm_sender the stream is done
			self.pcm_queue.put(None)

	# ------------------------------------------------------------------
	# PCM sender thread
	# ------------------------------------------------------------------

	def _pcm_sender(self) -> None:
		"""Dequeue PCM16 chunks and send to vLLM WebSocket."""
		while True:
			try:
				chunk = self.pcm_queue.get(timeout=1.0)
			except Empty:
				if not self.is_recording:
					break
				continue

			if chunk is None:
				break  # ffmpeg reader signalled end of stream

			if self.ws:
				try:
					self.ws.send(json.dumps({
						"type": "input_audio_buffer.append",
						"audio": base64.b64encode(chunk).decode("utf-8"),
					}))
				except Exception as e:
					print(f"[VOXTRAL] WebSocket send error: {e}")

	# ------------------------------------------------------------------
	# WebSocket callbacks
	# ------------------------------------------------------------------

	def _on_ws_open(self, ws) -> None:
		self.ws_connected.set()
		print(f"[VOXTRAL] WebSocket connected to vLLM")

	def _on_ws_message(self, ws, message: str) -> None:
		try:
			event = json.loads(message)
		except Exception:
			return

		event_type = event.get("type", "")

		if event_type == "session.created":
			# Configure model and signal start of audio stream
			try:
				ws.send(json.dumps({
					"type": "session.update",
					"model": VOXTRAL_MODEL,
				}))
				ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
				self.ws_ready.set()
				print(f"[VOXTRAL] Session ready, streaming to {VOXTRAL_MODEL}")
			except Exception as e:
				print(f"[VOXTRAL] Session setup error: {e}")

		elif event_type == "transcription.delta":
			delta = event.get("delta", "")
			self.current_delta += delta
			print(f"[VOXTRAL DELTA] {delta}", end="", flush=True)

		elif event_type == "transcription.done":
			text = event.get("text", "").strip()
			print(f"\n[VOXTRAL DONE] {text}")
			if text:
				self._process_transcription(text)
			self.current_delta = ""

		elif event_type == "error":
			print(f"[VOXTRAL] Server error: {event}")

	def _on_ws_error(self, ws, error) -> None:
		print(f"[VOXTRAL] WebSocket error: {error}")

	def _on_ws_close(self, ws, close_status_code, close_msg) -> None:
		print(f"[VOXTRAL] WebSocket closed: {close_status_code} {close_msg}")

	# ------------------------------------------------------------------
	# Word processing
	# ------------------------------------------------------------------

	def _process_transcription(self, text: str) -> None:
		"""Convert a completed Voxtral utterance into WordNodes."""
		cleaned = clean_transcription_text(text)
		tokens = nltk.word_tokenize(cleaned.lower())
		tokens = [t for t in tokens if t.isalnum()]

		with self.word_lock:
			for token in tokens:
				node = WordNode(
					word=token,
					start_time=datetime.now(),
					end_time=datetime.now(),
				)
				if self.last_node:
					self.last_node.next = node
					node.prev = self.last_node
				self.last_node = node
				self.word_queue.put(node)
				print(f"[WORD] '{token}'")

	def add_words_to_queue(self, word_nodes: List[WordNode]) -> None:
		if word_nodes:
			with self.word_lock:
				if self.last_node:
					self.last_node.next = word_nodes[0]
					word_nodes[0].prev = self.last_node
				self.last_node = word_nodes[-1]
				for node in word_nodes:
					self.word_queue.put(node)


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def get_stream(session_id: str) -> VoxtralWordStream:
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return VoxtralWordStream.streams[session_id]


# ---------------------------------------------------------------------------
# SocketIO events (same interface as WhisperLiveKitWordStream)
# ---------------------------------------------------------------------------

@VoxtralWordStream.socketio.on('connect')
def handle_connect():
	pass


@VoxtralWordStream.socketio.on('disconnect')
def handle_disconnect():
	pass


@VoxtralWordStream.socketio.on('start_listening')
def _start_listening(data: dict):
	session_id = data.get('session_id')
	mime_type = data.get("mime_type", "audio/webm")
	get_stream(session_id)._start_listening(mime_type)


@VoxtralWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict = None):
	session_id = data.get('session_id')
	get_stream(session_id)._stop_listening()


@VoxtralWordStream.socketio.on('audio_chunk')
def _handle_audio_chunk(data):
	session_id = data.get("session_id")
	audio_data = data.get("audio_data")
	get_stream(session_id)._handle_audio_chunk(audio_data)


@VoxtralWordStream.socketio.on('manual_text_entry')
def handle_manual_text_entry(data: dict):
	session_id = data.get('session_id')
	text = data.get('text', '')
	if session_id and text:
		word_stream = get_stream(session_id)
		if word_stream:
			words = word_stream.process_text(text)
			word_stream.add_words_to_queue(words)


# ---------------------------------------------------------------------------
# HTTP endpoints (mirrors WhisperLiveKitWordStream for compatibility)
# ---------------------------------------------------------------------------

@VoxtralWordStream.bp.route('/start_listening', methods=['POST'])
def http_start_listening():
	data = request.get_json()
	session_id = data.get('session_id')
	mime_type = data.get('mime_type', 'audio/webm')
	if not session_id:
		return jsonify({"error": "Missing session_id"}), 400
	try:
		get_stream(session_id)._start_listening(mime_type)
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/stop_listening', methods=['POST'])
def http_stop_listening():
	data = request.get_json()
	session_id = data.get('session_id')
	if not session_id:
		return jsonify({"error": "Missing session_id"}), 400
	try:
		get_stream(session_id)._stop_listening()
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/audio_chunk', methods=['POST'])
def http_audio_chunk():
	session_id = request.form.get('session_id')
	audio_file = request.files.get('audio_data')
	if not session_id or not audio_file:
		return jsonify({"error": "Missing session_id or audio_data"}), 400
	try:
		audio_data = audio_file.read()
		get_stream(session_id)._handle_audio_chunk(audio_data)
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/recorder')
def recorder():
	session_id = request.args.get('session')
	if not session_id:
		return "No session ID provided", 400
	return render_template('recorder.html', session_id=session_id)
