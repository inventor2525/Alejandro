from typing import Optional, Iterator, Dict, List
from .WordStream import WordStream, WordNode
from flask import Blueprint, jsonify, Response, request, Flask, render_template
from flask_socketio import SocketIO
from io import BufferedWriter
from queue import Queue, Empty
from datetime import datetime, timedelta
import json
import os
import time
import threading
import string
import base64
import asyncio
import logging

# Suppress INFO-level logs from WhisperLiveKit, werkzeug, and dependencies
logging.getLogger('whisperlivekit').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Import WhisperLiveKit components
from whisperlivekit import TranscriptionEngine, AudioProcessor

_transcription_engine = TranscriptionEngine(model="large-v3", diarization=False, lan="en")

mime_to_config = {
	"audio/webm": ("webm", "opus"),
	"audio/ogg": ("ogg", "opus"),
	"audio/wav": ("wav", "pcm_s16le"),
	"audio/mpeg": ("mp3", "mp3"),
	"audio/aac": ("aac", "aac"),
}

class WhisperLiveKitWordStream(WordStream):
	bp = Blueprint('WhisperLiveKitWordStream', __name__)
	socketio: SocketIO = SocketIO(
		ping_interval=25,  # Increase from default 25s to reduce polling
		ping_timeout=60,   # Increase timeout
		max_http_buffer_size=10000000  # 10MB for larger chunks
	)
	streams: Dict[str, 'WhisperLiveKitWordStream'] = {}

	def __init__(
		self,
		save_directory: Optional[str],
		session_id: Optional[str] = None
	):
		'''
		save_directory should be the folder that all
		recordings and their transcriptions will be
		stored in.

		Note: TranscriptionEngine settings (model, diarization, language) are
		configured at module import time and shared across all instances.
		'''
		# Setup a word stream for each session:
		self.session_id = session_id
		WhisperLiveKitWordStream.streams[session_id] = self

		# Setup save directory (All client audio should be saved here):
		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)
			# Create WhisperLiveKit output directory alongside recordings
			parent_dir = os.path.dirname(save_directory)
			self.wlk_output_dir = os.path.join(parent_dir, "WhisperLiveKitOutput")
			os.makedirs(self.wlk_output_dir, exist_ok=True)
		else:
			self.wlk_output_dir = None

		# AudioProcessor (created per-session, uses shared TranscriptionEngine)
		self.audio_processor: Optional['AudioProcessor'] = None

		# Async processing:
		self.audio_chunk_queue: Queue = Queue()  # Queue for audio chunks to process
		self.processing_loop: Optional[asyncio.AbstractEventLoop] = None
		self.processing_thread: Optional[threading.Thread] = None
		self.results_task: Optional[asyncio.Task] = None
		self.finalization_thread: Optional[threading.Thread] = None

		# State:
		self._running = True
		'''Used only once to close the client session.'''
		self.is_recording = False
		'''Toggled on start_listening and stop_listening.'''
		self.word_queue = Queue()
		'''All words that we have transcribed but that have not yet been consumed by the 'words' iterator.'''

		# For saving the current audio:
		self.current_audio_path: str = None
		self.current_audio_file: BufferedWriter = None
		self.start_time: datetime = None
		self.end_time: datetime = None

		self.last_node: WordNode = None
		self.transcription_lock = threading.Lock()

		# Track pending text segments for stability checking
		self.pending_segments = []  # List of {"text": str, "timestamp": float}
		self.last_finalized_len = 0  # How many characters of cumulative text we've finalized
		self.last_seen_transcription = ""  # To skip duplicate transcriptions
		self.stability_threshold = 0.5  # Seconds to wait before finalizing text

	@staticmethod
	def init_app(app: Flask):
		print("[INIT] Initializing WhisperLiveKitWordStream with Flask app")
		WhisperLiveKitWordStream.socketio.init_app(app)
		app.register_blueprint(WhisperLiveKitWordStream.bp)
		print(f"[INIT] SocketIO instance: {WhisperLiveKitWordStream.socketio}")
		print(f"[INIT] Registered handlers: {WhisperLiveKitWordStream.socketio.server.handlers}")

	def words(self) -> Iterator[WordNode]:
		'''
		Iterates all words produced by this live
		transcription of the client's microphone.

		Words are in the form of a linked list with
		time stamps to do rule based verbal UI control.
		'''
		while self._running:
			try:
				yield self.word_queue.get(block=True, timeout=0.5)
			except Empty:
				pass
		return

	def close(self):
		'''
		Stops any 'self.words' iterator (or thread iterating it).
		'''
		self._stop_listening()
		self._running = False
		if self.session_id in WhisperLiveKitWordStream.streams:
			del WhisperLiveKitWordStream.streams[self.session_id]

	def _init_audio_processor(self):
		'''
		Initialize the AudioProcessor for this session.
		Uses the global TranscriptionEngine.
		Starts async processing thread.
		'''
		print(f"[WLK] Starting async processing thread for session {self.session_id}")

		# Start the async processing thread
		self.processing_thread = threading.Thread(
			target=self._run_async_processor,
			daemon=True
		)
		self.processing_thread.start()

		# Give it a moment to initialize
		time.sleep(0.5)
		print("[WLK] AudioProcessor thread started successfully")

	def _run_async_processor(self):
		'''
		Run the async AudioProcessor in a separate thread with its own event loop.
		This method runs in a separate thread.
		'''
		try:
			print("[WLK] _run_async_processor: Starting...", flush=True)
			# Create new event loop for this thread
			self.processing_loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self.processing_loop)
			print("[WLK] _run_async_processor: Event loop created", flush=True)

			# Run the async processing
			self.processing_loop.run_until_complete(self._async_process_audio())
			print("[WLK] _run_async_processor: Completed normally", flush=True)

		except Exception as e:
			print(f"[WLK] Error in async processor thread: {e}", flush=True)
			import traceback
			traceback.print_exc()
		finally:
			print("[WLK] _run_async_processor: Cleaning up event loop...", flush=True)
			if self.processing_loop:
				self.processing_loop.close()
			print("[WLK] _run_async_processor: Thread exiting", flush=True)

	async def _async_process_audio(self):
		'''
		Async method that processes audio chunks.
		This is the main async processing loop.
		'''
		try:
			print("[WLK] _async_process_audio: Starting...", flush=True)

			# Create AudioProcessor for this session using the global TranscriptionEngine
			print(f"[WLK] Creating AudioProcessor for session {self.session_id}", flush=True)
			self.audio_processor = await asyncio.to_thread(
				AudioProcessor,
				transcription_engine=_transcription_engine
			)
			print(f"[WLK] AudioProcessor created successfully", flush=True)

			# Create tasks and get results generator
			print("[WLK] Calling create_tasks()...", flush=True)
			results_generator = await self.audio_processor.create_tasks()
			print(f"[WLK] create_tasks() returned: {type(results_generator)}", flush=True)

			# Start results handler task
			print("[WLK] Starting results handler task...", flush=True)
			self.results_task = asyncio.create_task(
				self._handle_transcription_results(results_generator)
			)
			print("[WLK] Results handler task started", flush=True)

			print("[WLK] AudioProcessor initialized, processing audio chunks...", flush=True)
			print(f"[WLK] Initial state: is_recording={self.is_recording}, queue_size={self.audio_chunk_queue.qsize()}", flush=True)

			# Process audio chunks from queue
			while self.is_recording or not self.audio_chunk_queue.empty():
				try:
					# Get audio chunk from queue (non-blocking with timeout)
					if not self.audio_chunk_queue.empty():
						audio_chunk = self.audio_chunk_queue.get_nowait()

						# Process the audio chunk
						await self.audio_processor.process_audio(audio_chunk)
					else:
						# Small sleep to avoid busy waiting
						await asyncio.sleep(0.01)

				except Empty:
					await asyncio.sleep(0.01)
				except Exception as e:
					print(f"[WLK] Error processing audio chunk: {e}", flush=True)
					import traceback
					traceback.print_exc()

			print("[WLK] Audio processing loop finished", flush=True)

			# Wait for results handler to finish
			if self.results_task:
				print("[WLK] Waiting for results handler to finish...", flush=True)
				await self.results_task
				print("[WLK] Results handler finished", flush=True)

		except Exception as e:
			print(f"[WLK] Error in async audio processing: {e}", flush=True)
			import traceback
			traceback.print_exc()

	async def _handle_transcription_results(self, results_generator):
		'''
		Async method that handles transcription results from the generator.
		'''
		try:
			async for result in results_generator:
				# Process results silently - detailed logging happens in _process_wlk_transcription
				if result:
					self._process_wlk_transcription(result)
		except Exception as e:
			print(f"[WLK] Error handling transcription results: {e}")
			import traceback
			traceback.print_exc()

	def _close_audio_processor(self):
		'''Close the AudioProcessor for this session'''
		try:
			print(f"[WLK] Closing AudioProcessor for session {self.session_id}")

			# Stop is_recording to signal the async loop to finish
			# (already done in _stop_listening, but just in case)

			# Wait for processing thread to finish
			if self.processing_thread and self.processing_thread.is_alive():
				print("[WLK] Waiting for processing thread to finish...")
				self.processing_thread.join(timeout=2.0)

			# Clean up
			self.audio_processor = None
			self.processing_loop = None
			self.processing_thread = None
			self.results_task = None

			print("[WLK] AudioProcessor closed")

		except Exception as e:
			print(f"[WLK] Error closing AudioProcessor: {e}")
			import traceback
			traceback.print_exc()

	def _start_listening(self, mime_type: str) -> None:
		'''
		Start recording client audio chunks to file
		and initialize WhisperLiveKit AudioProcessor.
		'''
		self.start_time = datetime.now()
		timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")

		self.file_ext = mime_to_config[mime_type][0]
		self.current_audio_path = os.path.join(
			self.save_directory,
			f"raw_recording_{timestamp}.{self.file_ext}"
		)
		print(f"[FILE] Opening audio file: {self.current_audio_path}")
		self.current_audio_file = open(self.current_audio_path, "wb")

		# Set is_recording BEFORE starting processor thread to avoid race condition
		self.is_recording = True
		print(f"[START] Setting is_recording={self.is_recording} before initializing processor")

		# Initialize WhisperLiveKit AudioProcessor
		self._init_audio_processor()

		# Start finalization thread
		self.finalization_thread = threading.Thread(
			target=self._run_finalization_thread,
			daemon=True
		)
		self.finalization_thread.start()

		print(f"[START] Recording started successfully")

	def _stop_listening(self) -> None:
		'''
		Close WhisperLiveKit AudioProcessor and finalize audio recording.
		'''
		print(f"[STOP] Stopping recording...")
		self.end_time = datetime.now()

		# Close audio file
		if self.current_audio_file:
			self.current_audio_file.close()
			print(f"[FILE] Closed audio file")

		# Close WhisperLiveKit AudioProcessor
		self._close_audio_processor()

		# Rename the finished recording
		if self.current_audio_path and os.path.exists(self.current_audio_path):
			start_str = self.start_time.strftime("%Y%m%d_%H%M%S")
			end_str = self.end_time.strftime("%Y%m%d_%H%M%S")
			new_raw = os.path.join(
				self.save_directory,
				f"recording_{start_str}__{end_str}.{self.file_ext}"
			)
			os.rename(self.current_audio_path, new_raw)
			print(f"[FILE] Renamed recording to: {new_raw}")

		self.is_recording = False

		# Wait for finalization thread to finish
		if self.finalization_thread and self.finalization_thread.is_alive():
			self.finalization_thread.join(timeout=1.0)

		# Flush any pending segments before resetting
		with self.transcription_lock:
			import nltk
			for seg in self.pending_segments:
				tokens = nltk.word_tokenize(seg["text"].lower())
				tokens = [t for t in tokens if t.isalnum()]
				for token in tokens:
					node = WordNode(word=token, start_time=datetime.now(), end_time=datetime.now())
					if self.last_node:
						self.last_node.next = node
						node.prev = self.last_node
					self.last_node = node
					self.word_queue.put(node)

		# Reset segment tracking for next session
		self.pending_segments = []
		self.last_finalized_len = 0
		self.last_seen_transcription = ""

		print(f"[STOP] Recording stopped")

	def _handle_audio_chunk(self, data: bytes):
		"""
		Record audio chunk to file and queue for WhisperLiveKit processing.
		"""
		# Write to disk (CRITICAL: preserve this functionality!)
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		# Queue audio chunk for async processing
		if self.is_recording and self.processing_thread and self.processing_thread.is_alive():
			try:
				self.audio_chunk_queue.put(data)
			except Exception as e:
				print(f"[WLK] Error queuing audio chunk: {e}")
		else:
			if not self.processing_thread:
				print(f"[WLK] Not processing: processing thread not started")
			elif not self.processing_thread.is_alive():
				print(f"[WLK] Not processing: processing thread died")
			elif not self.is_recording:
				print(f"[WLK] Not processing: is_recording={self.is_recording}")

	def _process_wlk_transcription(self, front_data):
		def extract_segment_text():
			for segment in (front_data.lines if front_data.lines else []):
				if hasattr(segment, 'text') and segment.text:
					stripped = segment.text.strip()
					if stripped:
						yield stripped

		current_text = " ".join(extract_segment_text())

		if self.wlk_output_dir:
			now = datetime.now()
			timestamp_str = f"{now.year}_{now.month:02d}_{now.day:02d}__{now.hour:02d}_{now.minute:02d}_{now.second:02d}.{now.microsecond // 1000:03d}"
			output_file = os.path.join(self.wlk_output_dir, f"frontdata_{timestamp_str}.json")
			try:
				with open(output_file, 'w') as f:
					json.dump(front_data.to_dict(), f, indent=4, default=str)
			except Exception as e:
				print(f"[WLK] Failed to save FrontData: {e}")

		if not current_text:
			return

		with self.transcription_lock:
			# Skip duplicate transcriptions
			if current_text == self.last_seen_transcription:
				return

			print(f"[WLK] NEW TRANSCRIPTION: '{current_text}'")
			self.last_seen_transcription = current_text

			current_time = time.time()
			current_text_of_interest = current_text[self.last_finalized_len:]

			if not current_text_of_interest:
				return

			# Check which existing segments still match
			accumulated = ""
			for i, seg in enumerate(self.pending_segments):
				accumulated += seg["text"]
				if not current_text_of_interest.startswith(accumulated):
					# Text changed at this segment
					seg["timestamp"] = current_time
					self.pending_segments = self.pending_segments[:i+1]
					break

			# If current text is longer than accumulated segments, add new segment
			if len(current_text_of_interest) > len(accumulated):
				new_text = current_text_of_interest[len(accumulated):]
				self.pending_segments.append({"text": new_text, "timestamp": current_time})

			# Try to finalize stable segments
			self._finalize_stable_segments(current_time)

	def _finalize_stable_segments(self, current_time: float):
		"""Finalize segments that have been stable past the threshold."""
		num_to_finalize = 0
		for seg in self.pending_segments:
			if current_time - seg["timestamp"] > self.stability_threshold:
				num_to_finalize += 1
			else:
				break

		if num_to_finalize > 0:
			import nltk
			combined_text = "".join(seg["text"] for seg in self.pending_segments[:num_to_finalize])
			tokens = nltk.word_tokenize(combined_text.lower())
			tokens = [t for t in tokens if t.isalnum()]

			for token in tokens:
				node = WordNode(word=token, start_time=datetime.now(), end_time=datetime.now())
				if self.last_node:
					self.last_node.next = node
					node.prev = self.last_node
				self.last_node = node
				self.word_queue.put(node)

			self.last_finalized_len += len(combined_text)
			self.pending_segments = self.pending_segments[num_to_finalize:]

	def _run_finalization_thread(self):
		"""Background thread that periodically checks and finalizes stable segments."""
		while self.is_recording:
			time.sleep(0.1)  # Check every 100ms
			with self.transcription_lock:
				if self.pending_segments:
					self._finalize_stable_segments(time.time())


def get_stream(session_id: str) -> WhisperLiveKitWordStream:
	'''
	Gets the word stream for the given session.
	'''
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return WhisperLiveKitWordStream.streams[session_id]


@WhisperLiveKitWordStream.socketio.on('connect')
def handle_connect():
	print("[SOCKETIO] Client connected!")


@WhisperLiveKitWordStream.socketio.on('disconnect')
def handle_disconnect():
	print("[SOCKETIO] Client disconnected!")


@WhisperLiveKitWordStream.socketio.on('start_listening')
def _start_listening(data: dict) -> Response:
	'''
	Receive the client command to start listening.

	This will establish a connection to WhisperLiveKit
	and start streaming audio for transcription.
	'''
	print(f"[EVENT] start_listening event received with data: {data}")
	session_id = data.get('session_id')
	mime_type = data.get("mime_type", "audio/webm")
	print(f"[START] Starting listening for session={session_id}, mime_type={mime_type}")
	get_stream(session_id)._start_listening(mime_type)


@WhisperLiveKitWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict = None) -> Response:
	'''
	Receive the client command to stop listening.
	'''
	session_id = data.get('session_id')
	print(f"[STOP] Stopping listening for session={session_id}")
	get_stream(session_id)._stop_listening()


@WhisperLiveKitWordStream.socketio.on("audio_chunk")
def _handle_audio_chunk(data):
	'''
	Receive a live audio chunk from the client microphone.
	Records to file and sends to WhisperLiveKit.
	'''
	session_id = data.get("session_id")
	audio_data = data.get("audio_data")
	print(f"[AUDIO] Received audio chunk from client, session={session_id}, size={len(audio_data) if audio_data else 0}")
	get_stream(session_id)._handle_audio_chunk(audio_data)


@WhisperLiveKitWordStream.socketio.on('manual_text_entry')
def handle_manual_text_entry(data: dict):
	'''
	Input manually typed text into the word queue
	as though it had been transcribed from speech.
	'''
	session_id = data.get('session_id')
	text = data.get('text', '')

	if session_id and text:
		word_stream = get_stream(session_id)
		if word_stream:
			words = word_stream.process_text(text)
			word_stream.add_words_to_queue(words)


@WhisperLiveKitWordStream.bp.route('/start_listening', methods=['POST'])
def http_start_listening():
	'''
	HTTP endpoint for starting listening session.
	Avoids SocketIO to bypass rate limits.
	'''
	data = request.get_json()
	session_id = data.get('session_id')
	mime_type = data.get('mime_type', 'audio/webm')

	if not session_id:
		return jsonify({"error": "Missing session_id"}), 400

	try:
		print(f"[HTTP] start_listening for session={session_id}, mime={mime_type}")
		get_stream(session_id)._start_listening(mime_type)
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		print(f"[HTTP] Error starting listening: {e}")
		return jsonify({"error": str(e)}), 500


@WhisperLiveKitWordStream.bp.route('/stop_listening', methods=['POST'])
def http_stop_listening():
	'''
	HTTP endpoint for stopping listening session.
	Avoids SocketIO to bypass rate limits.
	'''
	data = request.get_json()
	session_id = data.get('session_id')

	if not session_id:
		return jsonify({"error": "Missing session_id"}), 400

	try:
		print(f"[HTTP] stop_listening for session={session_id}")
		get_stream(session_id)._stop_listening()
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		print(f"[HTTP] Error stopping listening: {e}")
		return jsonify({"error": str(e)}), 500


@WhisperLiveKitWordStream.bp.route('/audio_chunk', methods=['POST'])
def http_audio_chunk():
	'''
	HTTP endpoint for receiving audio chunks.
	This avoids SocketIO payload size limits for large audio blobs.
	'''
	session_id = request.form.get('session_id')
	audio_file = request.files.get('audio_data')

	if not session_id or not audio_file:
		return jsonify({"error": "Missing session_id or audio_data"}), 400

	try:
		audio_data = audio_file.read()
		get_stream(session_id)._handle_audio_chunk(audio_data)
		return jsonify({"status": "ok"}), 200
	except Exception as e:
		print(f"[AUDIO] Error processing audio chunk: {e}")
		return jsonify({"error": str(e)}), 500


@WhisperLiveKitWordStream.bp.route('/recorder')
def recorder():
	'''
	Render a page meant to let the user start & stop recording
	as well as manually input typed text to the word queue as
	though it had been live transcribed from spoken word.
	'''
	session_id = request.args.get('session')
	if not session_id:
		return "No session ID provided", 400
	return render_template('recorder.html', session_id=session_id)
