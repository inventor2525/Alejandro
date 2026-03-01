"""
VoxtralWordStream — drop-in replacement for WhisperLiveKitWordStream.

Uses Voxtral-Mini-4B-Realtime via vLLM's OpenAI Realtime-compatible
WebSocket API.  Mirrors the WhisperLiveKitWordStream interface exactly so
session.py and app.py need no changes beyond the backend selection flag.

Key design goals:
  - words() iterator yields only COMPLETED words (never mid-token fragments)
  - Words are split using NLTK tokenization with a configurable
    WORD_EMIT_TIMEOUT_S fallback so a partial last-word is not held forever
  - Linked list of WordNodes is maintained (prev/next) for phrase matching
  - Every audio chunk is written to disk before anything else — loss is
    unacceptable; saving is the top priority
  - No web UI beyond the shared recorder.html template

vLLM endpoint is configured via env vars:
  VOXTRAL_HOST  (default: localhost)
  VOXTRAL_PORT  (default: 8000)
  VOXTRAL_MODEL (default: mistralai/Voxtral-Mini-4B-Realtime-2602)

Why ffmpeg?
  The browser's MediaRecorder API emits compressed WebM/Opus containers.
  vLLM's Realtime API input_audio_buffer.append only accepts raw PCM16 at
  16 kHz mono (base64-encoded) — it does NOT accept WebM or Opus directly.
  ffmpeg runs as a subprocess reading from stdin and writing raw PCM to
  stdout, acting as a live demux+decode pipeline with no temp files.
"""

import base64
import collections
import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from io import BufferedWriter
from queue import Empty, Queue
from typing import Dict, Iterator, List, Optional

import nltk
import websocket  # websocket-client
from flask import Blueprint, Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from .WordNode import WordNode
from .WordStream import WordStream

logger = logging.getLogger(__name__)

# ── Ensure NLTK data is available ────────────────────────────────────────────
for _corpus in ('punkt', 'punkt_tab'):
	try:
		nltk.data.find(f'tokenizers/{_corpus}')
	except LookupError:
		nltk.download(_corpus, quiet=True)

# ── Configuration ─────────────────────────────────────────────────────────────
VLLM_HOST     = os.environ.get("VOXTRAL_HOST",  "localhost")
VLLM_PORT     = int(os.environ.get("VOXTRAL_PORT",  "8000"))
VOXTRAL_MODEL = os.environ.get("VOXTRAL_MODEL", "mistralai/Voxtral-Mini-4B-Realtime-2602")

# 150 wpm ≈ one word every 400 ms — flush partial word if nothing new arrives.
WORD_EMIT_TIMEOUT_S: float = 0.4

PCM_CHUNK_BYTES = 3200  # 100 ms of PCM16 16 kHz mono

mime_to_ffmpeg_fmt: Dict[str, str] = {
	"audio/webm": "webm",
	"audio/ogg":  "ogg",
	"audio/wav":  "wav",
	"audio/mpeg": "mp3",
	"audio/aac":  "aac",
}

# ═══════════════════════════════════════════════════════════════════════════════
# DEBUG — Timing & Audio Snapshot
#
# DEBUG_TIMING  — prints average inter-chunk intervals every 5 s to console so
#                 you can spot which pipeline stage is falling behind over time.
#                 Three probes:
#                   [TIMING/client]   time between calls to _handle_audio_chunk
#                   [TIMING/pcm-out]  time between PCM chunks read from ffmpeg
#                   [TIMING/ws-send]  time between WebSocket sends to vLLM
#                 Plus pcm_queue depth on every print so you can see if chunks
#                 are piling up between ffmpeg and the sender.
#
# DEBUG_SNAPSHOT — enables the POST /voxtral/snapshot endpoint.
#                  Keeps a rolling SNAPSHOT_BUFFER_S-second deque of raw client
#                  chunks (timestamps + bytes) and decoded PCM chunks.  On
#                  request, dumps both to files so you can verify what's
#                  actually hitting vLLM is near-realtime.
#
# Set either to False to remove all overhead.
# ═══════════════════════════════════════════════════════════════════════════════
DEBUG_TIMING      = True
DEBUG_SNAPSHOT    = True

TIMING_PRINT_S    = 5.0   # how often to emit timing lines
SNAPSHOT_BUFFER_S = 30    # seconds of audio kept in rolling snapshot buffer


# ── Timing logger ─────────────────────────────────────────────────────────────

class _TimingLogger:
	"""
	Tracks wall-clock intervals between successive tick() calls and prints
	a summary line every TIMING_PRINT_S seconds.

	No-ops entirely when DEBUG_TIMING is False.
	"""
	def __init__(self, label: str):
		self.label       = label
		self._lock       = threading.Lock()
		self._last_ts:   Optional[float] = None
		self._intervals: List[float]     = []
		self._last_print: float          = time.monotonic()

	def tick(self) -> None:
		if not DEBUG_TIMING:
			return
		now = time.monotonic()
		with self._lock:
			if self._last_ts is not None:
				self._intervals.append(now - self._last_ts)
			self._last_ts = now
			elapsed = now - self._last_print
			if elapsed >= TIMING_PRINT_S and self._intervals:
				avg_ms = (sum(self._intervals) / len(self._intervals)) * 1000
				max_ms = max(self._intervals) * 1000
				print(
					f"[TIMING/{self.label}] "
					f"avg={avg_ms:.1f} ms  max={max_ms:.1f} ms  "
					f"n={len(self._intervals)}  over {elapsed:.1f} s"
				)
				self._intervals.clear()
				self._last_print = now


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
	"""Strip Whisper/Voxtral noise annotations before tokenization."""
	text = re.sub(r'\[([^\]]*?)\]', ' ', text)
	text = re.sub(r'\(([^\)]*?)\)', ' ', text)
	text = re.sub(r'\[([^\]]*?)$',  ' ', text)
	text = re.sub(r'\[([^\]]*?)\s', ' ', text)
	text = re.sub(r'\(([^\)]*?)$',  ' ', text)
	text = re.sub(r'\(([^\)]*?)\s', ' ', text)
	text = re.sub(r'([^\[]*?)\]',   ' ', text)
	text = re.sub(r'([^\(]*?)\)',   ' ', text)
	return re.sub(r'\s+', ' ', text).strip()


# ── Token accumulator ─────────────────────────────────────────────────────────

class _TokenAccumulator:
	"""
	Accumulates raw vLLM delta tokens and emits complete words.

	Voxtral streams sub-word BPE deltas, not full words.  We buffer them and
	emit a word whenever:
	  (a) the buffer contains a word boundary NLTK would split on, OR
	  (b) a transcription.done event fires (flush everything remaining), OR
	  (c) WORD_EMIT_TIMEOUT_S elapses since the last token (flush).

	Strategy: after each append, tokenize the buffer.  If there are ≥2 NLTK
	tokens, all tokens except the last are safe to emit (the last may still be
	mid-word).  Hold the last token until the next delimiter or flush.
	"""

	def __init__(self, emit_cb):
		self._buf     = ""
		self._emit    = emit_cb
		self._lock    = threading.Lock()
		self._last_ts = time.monotonic()
		self._watchdog = threading.Thread(target=self._watchdog_loop, daemon=True)
		self._watchdog.start()

	def append(self, delta: str) -> None:
		with self._lock:
			self._buf    += delta
			self._last_ts = time.monotonic()
			self._try_emit_safe()

	def flush(self) -> None:
		with self._lock:
			self._emit_all()

	def _try_emit_safe(self) -> None:
		tokens = self._tokenize(self._buf)
		if len(tokens) >= 2:
			for tok in tokens[:-1]:
				self._emit(tok)
			last_tok = tokens[-1]
			idx = self._buf.lower().rfind(last_tok)
			self._buf = self._buf[idx:] if idx >= 0 else ""

	def _emit_all(self) -> None:
		for tok in self._tokenize(self._buf):
			self._emit(tok)
		self._buf = ""

	@staticmethod
	def _tokenize(text: str) -> List[str]:
		cleaned = _clean(text)
		if not cleaned:
			return []
		tokens = nltk.word_tokenize(cleaned.lower())
		return [t for t in tokens if t.isalnum()]

	def _watchdog_loop(self) -> None:
		while True:
			time.sleep(0.1)
			with self._lock:
				if self._buf and (time.monotonic() - self._last_ts) > WORD_EMIT_TIMEOUT_S:
					logger.debug("[VOXTRAL] Token timeout — flushing partial word")
					self._emit_all()


# ── VoxtralWordStream ─────────────────────────────────────────────────────────

class VoxtralWordStream(WordStream):
	bp       = Blueprint('VoxtralWordStream', __name__)
	socketio = SocketIO(
		ping_interval=25,
		ping_timeout=60,
		max_http_buffer_size=10_000_000,
	)
	streams: Dict[str, 'VoxtralWordStream'] = {}

	def __init__(
		self,
		save_directory: Optional[str],
		session_id: Optional[str] = None,
	):
		self.session_id = session_id
		VoxtralWordStream.streams[session_id] = self

		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)

		self._running     = True
		self.is_recording = False
		self.word_queue: Queue = Queue()

		self.file_ext: str                             = "webm"
		self.current_audio_path: Optional[str]         = None
		self.current_audio_file: Optional[BufferedWriter] = None
		self.start_time: Optional[datetime]            = None
		self.end_time: Optional[datetime]              = None

		self.last_node: Optional[WordNode] = None
		self._word_lock = threading.Lock()

		# ffmpeg: compressed audio → PCM16 16 kHz mono
		self.ffmpeg_proc: Optional[subprocess.Popen]          = None
		self.ffmpeg_reader_thread: Optional[threading.Thread] = None
		self.pcm_queue: Queue = Queue(maxsize=200)

		# vLLM WebSocket
		self.ws: Optional[websocket.WebSocketApp] = None
		self.ws_thread: Optional[threading.Thread] = None
		self.ws_ready   = threading.Event()

		self.pcm_sender_thread: Optional[threading.Thread] = None

		self._accum = _TokenAccumulator(emit_cb=self._emit_word)

		# ── DEBUG: timing loggers ─────────────────────────────────────────────
		if DEBUG_TIMING:
			self._t_client  = _TimingLogger("client")   # chunk arrival from browser
			self._t_pcm_out = _TimingLogger("pcm-out")  # PCM chunk out of ffmpeg
			self._t_ws_send = _TimingLogger("ws-send")  # PCM chunk sent to vLLM

		# ── DEBUG: rolling audio snapshot buffers ─────────────────────────────
		# Each entry: (monotonic_timestamp, bytes)
		# Pruned to the last SNAPSHOT_BUFFER_S seconds on each append.
		if DEBUG_SNAPSHOT:
			self._raw_buf: collections.deque = collections.deque()  # compressed from client
			self._pcm_buf: collections.deque = collections.deque()  # raw PCM16 post-ffmpeg
			self._snap_lock = threading.Lock()

	# ── Alejandro interface ───────────────────────────────────────────────────

	@staticmethod
	def init_app(app: Flask) -> None:
		VoxtralWordStream.socketio.init_app(app)
		app.register_blueprint(VoxtralWordStream.bp)

	def words(self) -> Iterator[WordNode]:
		while self._running:
			try:
				yield self.word_queue.get(block=True, timeout=0.5)
			except Empty:
				pass

	def close(self) -> None:
		self._stop_listening()
		self._running = False
		VoxtralWordStream.streams.pop(self.session_id, None)

	# ── Recording lifecycle ───────────────────────────────────────────────────

	def _start_listening(self, mime_type: str) -> None:
		self.start_time = datetime.now()
		ts = self.start_time.strftime("%Y%m%d_%H%M%S")

		self.file_ext           = mime_to_ffmpeg_fmt.get(mime_type, "webm")
		self.current_audio_path = os.path.join(
			self.save_directory, f"raw_recording_{ts}.{self.file_ext}"
		)
		self.current_audio_file = open(self.current_audio_path, "wb")

		ffmpeg_fmt = mime_to_ffmpeg_fmt.get(mime_type, "webm")
		self.ffmpeg_proc = subprocess.Popen(
			[
				"ffmpeg", "-hide_banner", "-loglevel", "error",
				"-f", ffmpeg_fmt, "-i", "pipe:0",
				"-ar", "16000", "-ac", "1", "-f", "s16le", "pipe:1",
			],
			stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.DEVNULL,
		)
		self.ffmpeg_reader_thread = threading.Thread(
			target=self._ffmpeg_reader, daemon=True
		)
		self.ffmpeg_reader_thread.start()

		self.ws_ready.clear()
		ws_url = f"ws://{VLLM_HOST}:{VLLM_PORT}/v1/realtime"
		self.ws = websocket.WebSocketApp(
			ws_url,
			on_open=self._on_ws_open,
			on_message=self._on_ws_message,
			on_error=self._on_ws_error,
			on_close=self._on_ws_close,
		)
		self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
		self.ws_thread.start()

		if not self.ws_ready.wait(timeout=10.0):
			logger.warning("[VOXTRAL] Could not connect to vLLM within 10 s")

		self.is_recording = True

		self.pcm_sender_thread = threading.Thread(
			target=self._pcm_sender, daemon=True
		)
		self.pcm_sender_thread.start()

	def _stop_listening(self) -> None:
		self.end_time     = datetime.now()
		self.is_recording = False

		if self.current_audio_file:
			self.current_audio_file.close()

		if self.ffmpeg_proc and self.ffmpeg_proc.stdin:
			try:
				self.ffmpeg_proc.stdin.close()
			except Exception:
				pass

		if self.pcm_sender_thread and self.pcm_sender_thread.is_alive():
			self.pcm_sender_thread.join(timeout=5.0)

		self._accum.flush()

		if self.ws:
			try:
				self.ws.send(json.dumps({
					"type": "input_audio_buffer.commit", "final": True
				}))
				time.sleep(0.5)
			except Exception:
				pass
			try:
				self.ws.close()
			except Exception:
				pass

		if self.ws_thread and self.ws_thread.is_alive():
			self.ws_thread.join(timeout=3.0)

		if self.current_audio_path and os.path.exists(self.current_audio_path):
			start_s = self.start_time.strftime("%Y%m%d_%H%M%S")
			end_s   = self.end_time.strftime("%Y%m%d_%H%M%S")
			new_path = os.path.join(
				self.save_directory,
				f"recording_{start_s}__{end_s}.{self.file_ext}"
			)
			os.rename(self.current_audio_path, new_path)

	def _handle_audio_chunk(self, data: bytes) -> None:
		# PRIORITY 1: save to disk immediately, unconditionally
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		if self.is_recording and self.ffmpeg_proc and self.ffmpeg_proc.stdin:
			try:
				self.ffmpeg_proc.stdin.write(data)
				self.ffmpeg_proc.stdin.flush()
			except Exception:
				pass

		# ── DEBUG: timing + snapshot ──────────────────────────────────────────
		if DEBUG_TIMING:
			self._t_client.tick()

		if DEBUG_SNAPSHOT:
			now = time.monotonic()
			with self._snap_lock:
				self._raw_buf.append((now, data))
				cutoff = now - SNAPSHOT_BUFFER_S
				while self._raw_buf and self._raw_buf[0][0] < cutoff:
					self._raw_buf.popleft()

	# ── Internal audio threads ────────────────────────────────────────────────

	def _ffmpeg_reader(self) -> None:
		try:
			while True:
				chunk = self.ffmpeg_proc.stdout.read(PCM_CHUNK_BYTES)
				if not chunk:
					break
				try:
					self.pcm_queue.put(chunk, timeout=2.0)
				except Exception:
					pass

				# ── DEBUG: timing + snapshot ──────────────────────────────────
				if DEBUG_TIMING:
					self._t_pcm_out.tick()

				if DEBUG_SNAPSHOT:
					now = time.monotonic()
					with self._snap_lock:
						self._pcm_buf.append((now, chunk))
						cutoff = now - SNAPSHOT_BUFFER_S
						while self._pcm_buf and self._pcm_buf[0][0] < cutoff:
							self._pcm_buf.popleft()

		except Exception as e:
			logger.error(f"[VOXTRAL] ffmpeg reader: {e}")
		finally:
			self.pcm_queue.put(None)

	def _pcm_sender(self) -> None:
		while True:
			try:
				chunk = self.pcm_queue.get(timeout=1.0)
			except Empty:
				if not self.is_recording:
					break
				continue
			if chunk is None:
				break
			if self.ws:
				try:
					self.ws.send(json.dumps({
						"type":  "input_audio_buffer.append",
						"audio": base64.b64encode(chunk).decode(),
					}))
				except Exception as e:
					logger.error(f"[VOXTRAL] WS send: {e}")

			# ── DEBUG: timing + queue depth ───────────────────────────────────
			if DEBUG_TIMING:
				self._t_ws_send.tick()
				# Piggyback queue depth onto the ws-send print: override last
				# interval print to also show pcm_queue depth.
				# We just check here — the _TimingLogger above handles printing.
				qd = self.pcm_queue.qsize()
				if qd > 10:
					print(f"[TIMING/pcm-queue] depth={qd}  (>10 means backpressure)")

	# ── WebSocket callbacks ───────────────────────────────────────────────────

	def _on_ws_open(self, ws) -> None:
		logger.info("[VOXTRAL] WebSocket connected")

	def _on_ws_message(self, ws, message: str) -> None:
		try:
			event = json.loads(message)
		except Exception:
			return

		t = event.get("type", "")

		if t == "session.created":
			try:
				ws.send(json.dumps({"type": "session.update", "model": VOXTRAL_MODEL}))
				ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
				self.ws_ready.set()
			except Exception as e:
				logger.error(f"[VOXTRAL] Session setup: {e}")

		elif t == "transcription.delta":
			delta = event.get("delta", "")
			if delta:
				self._accum.append(delta)

		elif t == "transcription.done":
			self._accum.flush()

		elif t == "error":
			logger.error(f"[VOXTRAL] Server error: {event}")

	def _on_ws_error(self, ws, error) -> None:
		logger.error(f"[VOXTRAL] WS error: {error}")

	def _on_ws_close(self, ws, code, msg) -> None:
		logger.info(f"[VOXTRAL] WS closed: {code} {msg}")

	# ── Word emission ─────────────────────────────────────────────────────────

	def _emit_word(self, word: str) -> None:
		node = WordNode(
			word=word,
			start_time=datetime.now(),
			end_time=datetime.now(),
		)
		with self._word_lock:
			if self.last_node:
				self.last_node.next = node
				node.prev = self.last_node
			self.last_node = node
			self.word_queue.put(node)
		print(f"[WORD] '{word}'")

	def add_words_to_queue(self, word_nodes: List[WordNode]) -> None:
		"""Inject pre-built WordNodes (e.g. from manual text entry)."""
		if not word_nodes:
			return
		with self._word_lock:
			if self.last_node:
				self.last_node.next = word_nodes[0]
				word_nodes[0].prev = self.last_node
			self.last_node = word_nodes[-1]
			for n in word_nodes:
				self.word_queue.put(n)

	# ── DEBUG: snapshot dump ──────────────────────────────────────────────────

	def _dump_snapshot(self) -> dict:
		"""
		Saves the last SNAPSHOT_BUFFER_S seconds of raw and PCM audio to
		the save_directory and returns a timing-analysis dict.

		Raw file:  snapshot_raw_<ts>.webm  — compressed stream from client
		PCM file:  snapshot_pcm_<ts>.raw   — decoded PCM16 16 kHz mono
		  Play:  ffplay -f s16le -ar 16000 -ac 1 snapshot_pcm_<ts>.raw

		Returns a dict with inter-chunk timing stats for both buffers and
		the current pcm_queue depth.
		"""
		if not DEBUG_SNAPSHOT:
			return {"error": "DEBUG_SNAPSHOT is disabled"}

		ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

		with self._snap_lock:
			raw_entries = list(self._raw_buf)
			pcm_entries = list(self._pcm_buf)

		def _interval_stats(entries):
			if len(entries) < 2:
				return {"n": len(entries), "note": "not enough data"}
			intervals = [
				(entries[i+1][0] - entries[i][0]) * 1000
				for i in range(len(entries) - 1)
			]
			return {
				"n":       len(entries),
				"avg_ms":  round(sum(intervals) / len(intervals), 1),
				"max_ms":  round(max(intervals), 1),
				"min_ms":  round(min(intervals), 1),
				"span_s":  round(entries[-1][0] - entries[0][0], 2),
			}

		result = {
			"ts":            ts,
			"raw_chunks":    _interval_stats(raw_entries),
			"pcm_chunks":    _interval_stats(pcm_entries),
			"pcm_queue_now": self.pcm_queue.qsize(),
			"is_recording":  self.is_recording,
		}

		# Save files
		if self.save_directory:
			if raw_entries:
				raw_path = os.path.join(self.save_directory, f"snapshot_raw_{ts}.{self.file_ext}")
				with open(raw_path, "wb") as f:
					for _, chunk in raw_entries:
						f.write(chunk)
				result["raw_file"] = raw_path

			if pcm_entries:
				pcm_path = os.path.join(self.save_directory, f"snapshot_pcm_{ts}.raw")
				with open(pcm_path, "wb") as f:
					for _, chunk in pcm_entries:
						f.write(chunk)
				result["pcm_file"] = pcm_path
				result["pcm_play"] = f"ffplay -f s16le -ar 16000 -ac 1 {pcm_path}"

		print(f"[SNAPSHOT] {json.dumps(result, indent=2)}")
		return result


# ── Session helper ────────────────────────────────────────────────────────────

def get_stream(session_id: str) -> VoxtralWordStream:
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return VoxtralWordStream.streams[session_id]


# ── SocketIO events ───────────────────────────────────────────────────────────

@VoxtralWordStream.socketio.on('connect')
def handle_connect(): pass


@VoxtralWordStream.socketio.on('disconnect')
def handle_disconnect(): pass


@VoxtralWordStream.socketio.on('start_listening')
def _start_listening(data: dict):
	get_stream(data.get('session_id'))._start_listening(
		data.get("mime_type", "audio/webm")
	)


@VoxtralWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict = None):
	get_stream((data or {}).get('session_id'))._stop_listening()


@VoxtralWordStream.socketio.on('audio_chunk')
def _handle_audio_chunk(data):
	get_stream(data.get("session_id"))._handle_audio_chunk(data.get("audio_data"))


@VoxtralWordStream.socketio.on('manual_text_entry')
def handle_manual_text_entry(data: dict):
	sid  = data.get('session_id')
	text = data.get('text', '')
	if sid and text:
		ws = get_stream(sid)
		ws.add_words_to_queue(ws.process_text(text))


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@VoxtralWordStream.bp.route('/start_listening', methods=['POST'])
def http_start_listening():
	d = request.get_json()
	sid = d.get('session_id')
	if not sid:
		return jsonify({"error": "Missing session_id"}), 400
	try:
		get_stream(sid)._start_listening(d.get('mime_type', 'audio/webm'))
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/stop_listening', methods=['POST'])
def http_stop_listening():
	d = request.get_json()
	sid = d.get('session_id')
	if not sid:
		return jsonify({"error": "Missing session_id"}), 400
	try:
		get_stream(sid)._stop_listening()
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/audio_chunk', methods=['POST'])
def http_audio_chunk():
	sid        = request.form.get('session_id')
	audio_file = request.files.get('audio_data')
	if not sid or not audio_file:
		return jsonify({"error": "Missing session_id or audio_data"}), 400
	try:
		get_stream(sid)._handle_audio_chunk(audio_file.read())
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@VoxtralWordStream.bp.route('/recorder')
def recorder():
	sid = request.args.get('session')
	if not sid:
		return "No session ID provided", 400
	return render_template('recorder.html', session_id=sid)


@VoxtralWordStream.bp.route('/voxtral/snapshot', methods=['GET', 'POST'])
def audio_snapshot():
	"""
	Trigger an audio pipeline snapshot to diagnose latency buildup.

	Saves the last ~SNAPSHOT_BUFFER_S seconds of both raw incoming audio
	(from client) and decoded PCM audio (post-ffmpeg, pre-vLLM) to files,
	and returns inter-chunk timing stats as JSON.

	Usage (any session — picks the first active one):
	    curl -X POST https://localhost:5000/voxtral/snapshot
	    wget -qO- --no-check-certificate https://localhost:5000/voxtral/snapshot

	Usage (specific session):
	    curl -X POST "https://localhost:5000/voxtral/snapshot?session_id=<sid>"

	The returned JSON includes:
	  raw_chunks.avg_ms  — average gap between client audio chunks arriving
	  pcm_chunks.avg_ms  — average gap between PCM chunks out of ffmpeg
	  pcm_queue_now      — how many PCM chunks are queued waiting to send
	  raw_file / pcm_file — paths to the saved audio files

	To listen to the PCM snapshot and verify it sounds real-time:
	    ffplay -f s16le -ar 16000 -ac 1 <pcm_file>

	A growing pcm_queue_now or a pcm_chunks.avg_ms much larger than
	~100 ms indicates backpressure between ffmpeg and the vLLM sender.
	A raw_chunks.avg_ms growing over time indicates the client is slowing
	down or the network is buffering.
	"""
	if not DEBUG_SNAPSHOT:
		return jsonify({"error": "DEBUG_SNAPSHOT is disabled in VoxtralWordStream.py"}), 503

	sid = request.args.get('session_id')

	if sid:
		stream = VoxtralWordStream.streams.get(sid)
	else:
		# Pick the first active session
		stream = next(
			(s for s in VoxtralWordStream.streams.values() if s.is_recording),
			next(iter(VoxtralWordStream.streams.values()), None)
		)

	if not stream:
		return jsonify({"error": "No active VoxtralWordStream session found"}), 404

	result = stream._dump_snapshot()
	return jsonify(result), 200
