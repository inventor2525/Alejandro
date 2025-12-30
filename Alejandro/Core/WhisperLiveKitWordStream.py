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

# Import WhisperLiveKit components (required - will crash if not installed)
from whisperlivekit import TranscriptionEngine, AudioProcessor

# Global TranscriptionEngine (heavy - created once at module import)
# Shared across all WhisperLiveKitWordStream instances
print("[WLK] Initializing global TranscriptionEngine (model=large-v3, diarization=False, language=en)")
_transcription_engine = TranscriptionEngine(model="large-v3", diarization=False, lan="en")
print("[WLK] TranscriptionEngine ready")

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

		# AudioProcessor (created per-session, uses shared TranscriptionEngine)
		self.audio_processor: Optional['AudioProcessor'] = None

		# Async processing:
		self.audio_chunk_queue: Queue = Queue()  # Queue for audio chunks to process
		self.processing_loop: Optional[asyncio.AbstractEventLoop] = None
		self.processing_thread: Optional[threading.Thread] = None
		self.results_task: Optional[asyncio.Task] = None

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

		# For managing transcription:
		self.last_node: WordNode = None
		self.transcription_lock = threading.Lock()

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
						print(f"[WLK] Processing {len(audio_chunk)} bytes...", flush=True)
						await self.audio_processor.process_audio(audio_chunk)
						print(f"[WLK] Processed {len(audio_chunk)} bytes successfully", flush=True)
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
				print(f"[WLK] Received transcription result: {result}")
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

		self.file_ext = mime_to_config.get(mime_type, ("webm", "opus"))[0]
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
				print(f"[WLK] Queued {len(data)} bytes for processing (queue size: {self.audio_chunk_queue.qsize()})")
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
		'''
		Process transcription results from WhisperLiveKit.

		front_data is a FrontData object with fields:
		- status: str (e.g., 'active_transcription', 'no_audio_detected')
		- lines: List[Segment] - committed/final transcription segments (may include SilentSegment)
		- buffer_transcription: str - in-progress/buffered text
		- buffer_diarization: str - speaker info (we don't use)
		- buffer_translation: str - translation (we don't use)
		- error: str - error message if any
		'''
		# Convert FrontData to dict for inspection
		import json
		try:
			# Try to convert to dict if it has a to_dict method
			if hasattr(front_data, 'to_dict'):
				data_dict = front_data.to_dict()
			elif hasattr(front_data, '__dict__'):
				# Fallback: manually extract attributes
				data_dict = {}
				for key, value in front_data.__dict__.items():
					if isinstance(value, list):
						# Convert segments to dicts
						data_dict[key] = [
							seg.__dict__ if hasattr(seg, '__dict__') else str(seg)
							for seg in value
						]
					else:
						data_dict[key] = value
			else:
				data_dict = str(front_data)

			print(f"[WLK] FrontData received:")
			print(json.dumps(data_dict, indent=4, default=str))
		except Exception as e:
			print(f"[WLK] Could not serialize FrontData: {e}")
			print(f"[WLK] FrontData type: {type(front_data)}, dir: {dir(front_data)}")

		# Process committed lines (final transcriptions)
		if front_data.lines:
			with self.transcription_lock:
				for segment in front_data.lines:
					# Segments have a .text attribute
					if hasattr(segment, 'text') and segment.text and segment.text.strip():
						print(f"[WLK] FINAL: '{segment.text}'")
						word_nodes = self.process_text(segment.text)
						self.add_words_to_queue(word_nodes)

		# Process buffer (in-progress/real-time transcription chunks)
		# This gives us the "Hey, Alej" → "andro" behavior
		if front_data.buffer_transcription and front_data.buffer_transcription.strip():
			print(f"[WLK] BUFFER (real-time chunk): '{front_data.buffer_transcription}'")

	def _process_word_level_transcription(self, words_data: List[dict]):
		'''
		Process word-level transcription data with timestamps.
		'''
		for word_info in words_data:
			word_text = word_info.get('word', '')
			word_start = word_info.get('start', 0.0)
			word_end = word_info.get('end', 0.0)

			# Clean the word text (remove punctuation from edges)
			cleaned_text = word_text.strip()
			cleaned_text = cleaned_text.rstrip(string.punctuation)
			cleaned_text = cleaned_text.lstrip(string.punctuation)

			if cleaned_text:  # Only add non-empty words
				# Create WordNode with absolute timestamps
				word_node = WordNode(
					cleaned_text.lower(),
					self.start_time + timedelta(seconds=word_start),
					self.start_time + timedelta(seconds=word_end),
				)

				# Link to previous node
				self.last_node = WordNode.join_returning_next(
					prev=self.last_node,
					next=word_node
				)

				# Add to queue for consumption
				self.word_queue.put(self.last_node)
				print(f"[WLK] Added word to queue: '{cleaned_text}'")

	def _process_text_level_transcription(
		self,
		text: str,
		start_offset: float,
		end_offset: float
	):
		'''
		Process text-level transcription without word timestamps.
		Estimates word boundaries using NLTK tokenization.
		'''
		print(f"[WLK] Text-level transcription: '{text}'")
		word_nodes = self.process_text(text)

		if not word_nodes:
			print(f"[WLK] No words extracted from text")
			return

		print(f"[WLK] Extracted {len(word_nodes)} words from text")

		# Estimate timestamps for each word
		duration = end_offset - start_offset
		estimated_word_length = timedelta(seconds=duration / len(word_nodes))

		for index, node in enumerate(word_nodes):
			node.start_time = self.start_time + timedelta(seconds=start_offset) + index * estimated_word_length
			node.end_time = node.start_time + estimated_word_length

		# Link and queue the words
		self.add_words_to_queue(word_nodes)

	def add_words_to_queue(self, word_nodes: List[WordNode]):
		'''Add a list of word nodes to the queue'''
		if word_nodes:
			print(f"[WLK] Adding {len(word_nodes)} words to queue: {[n.word for n in word_nodes]}")
			# Link to previous node
			if self.last_node:
				self.last_node.set_next(word_nodes[0])

			# Update last node
			self.last_node = word_nodes[-1]

			# Add all nodes to queue
			for node in word_nodes:
				self.word_queue.put(node)


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
		print(f"[AUDIO] HTTP received audio chunk, session={session_id}, size={len(audio_data)}")
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
