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
import re

# Suppress INFO-level logs from WhisperLiveKit, werkzeug, and dependencies
logging.getLogger('whisperlivekit').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Import WhisperLiveKit components
from whisperlivekit import TranscriptionEngine, AudioProcessor

_transcription_engine = TranscriptionEngine(
	# distil-large-v3 is 6x faster than large-v3 with <1% WER difference.
	# Less processing lag means the model starts receiving speech earlier,
	# which helps with capturing utterance beginnings.
	# Switch back to "large-v3" if accuracy regresses noticeably.
	model="distil-large-v3",
	diarization=False,
	lan="en",
	# localagreement waits for consecutive-decode agreement before emitting tokens,
	# eliminating phrase-start mutilation (e.g. "Aleja"/"ndro" splits).
	backend_policy="localagreement",
	# Default no_speech_threshold is 0.6 — Whisper will silently drop segments
	# it classifies as "not speech" above this confidence. On a poor mic the model
	# can misclassify the beginning of an utterance, cutting off the first word.
	# 0.35 makes it more aggressive about treating audio as speech.
	no_speech_threshold=0.35,
	# Larger beam = better accuracy at slight speed cost.
	# distil-large-v3 is fast enough to absorb this comfortably.
	beam_size=8,
	min_chunk_size=.25,
	vac_chunk_size=.1,
)

mime_to_config = {
	"audio/webm": ("webm", "opus"),
	"audio/ogg": ("ogg", "opus"),
	"audio/wav": ("wav", "pcm_s16le"),
	"audio/mpeg": ("mp3", "mp3"),
	"audio/aac": ("aac", "aac"),
}

def clean_transcription_text(text: str) -> str:
	"""
	Clean transcription text by removing:
	- Complete square brackets and their content: [BLANK_AUDIO], [LAUGHTER]
	- Complete parentheses and their content: (laughing), (laughs)
	- Incomplete brackets/parentheses at boundaries: [BLANK, (laughing, text], text)

	This must be done BEFORE tokenization to avoid partial words leaking through.
	"""
	# Remove complete square brackets and content
	text = re.sub(r'\[([^\]]*?)\]', ' ', text)

	# Remove complete parentheses and content
	text = re.sub(r'\(([^\)]*?)\)', ' ', text)

	# Remove incomplete opening brackets at end or anywhere
	text = re.sub(r'\[([^\]]*?)$', ' ', text)  # [BLANK at end
	text = re.sub(r'\[([^\]]*?)\s', ' ', text)  # [BLANK in middle

	# Remove incomplete opening parentheses at end or anywhere
	text = re.sub(r'\(([^\)]*?)$', ' ', text)  # (laughing at end
	text = re.sub(r'\(([^\)]*?)\s', ' ', text)  # (laughing in middle

	# Remove incomplete closing brackets/parens (rare but possible)
	text = re.sub(r'([^\[]*?)\]', ' ', text)  # text]
	text = re.sub(r'([^\(]*?)\)', ' ', text)  # text)

	# Clean up multiple spaces
	text = re.sub(r'\s+', ' ', text).strip()

	return text

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

		# Cursor into WLK's cumulative text output (text is append-only with localagreement)
		self.last_finalized_len = 0
		self.last_seen_transcription = ""

	@staticmethod
	def init_app(app: Flask):
		WhisperLiveKitWordStream.socketio.init_app(app)
		app.register_blueprint(WhisperLiveKitWordStream.bp)

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

		# Start the async processing thread
		self.processing_thread = threading.Thread(
			target=self._run_async_processor,
			daemon=True
		)
		self.processing_thread.start()

		# Give it a moment to initialize
		time.sleep(0.5)

	def _run_async_processor(self):
		'''
		Run the async AudioProcessor in a separate thread with its own event loop.
		This method runs in a separate thread.
		'''
		try:
			# Create new event loop for this thread
			self.processing_loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self.processing_loop)

			# Run the async processing
			self.processing_loop.run_until_complete(self._async_process_audio())

		except Exception as e:
			import traceback
			traceback.print_exc()
		finally:
			if self.processing_loop:
				self.processing_loop.close()

	async def _async_process_audio(self):
		'''
		Async method that processes audio chunks.
		This is the main async processing loop.
		'''
		try:

			# Create AudioProcessor for this session using the global TranscriptionEngine
			self.audio_processor = await asyncio.to_thread(
				AudioProcessor,
				transcription_engine=_transcription_engine
			)

			# Create tasks and get results generator
			results_generator = await self.audio_processor.create_tasks()

			# Start results handler task
			self.results_task = asyncio.create_task(
				self._handle_transcription_results(results_generator)
			)


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
					import traceback
					traceback.print_exc()


			# Wait for results handler to finish
			if self.results_task:
				await self.results_task

		except Exception as e:
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
			import traceback
			traceback.print_exc()

	def _close_audio_processor(self):
		'''Close the AudioProcessor for this session'''
		try:

			# Stop is_recording to signal the async loop to finish
			# (already done in _stop_listening, but just in case)

			# Wait for processing thread to finish
			if self.processing_thread and self.processing_thread.is_alive():
				self.processing_thread.join(timeout=2.0)

			# Clean up
			self.audio_processor = None
			self.processing_loop = None
			self.processing_thread = None
			self.results_task = None


		except Exception as e:
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
		self.current_audio_file = open(self.current_audio_path, "wb")

		# Set is_recording BEFORE starting processor thread to avoid race condition
		self.is_recording = True
		
		# Initialize WhisperLiveKit AudioProcessor
		self._init_audio_processor()


	def _stop_listening(self) -> None:
		'''
		Close WhisperLiveKit AudioProcessor and finalize audio recording.
		'''
		self.end_time = datetime.now()

		# Close audio file
		if self.current_audio_file:
			self.current_audio_file.close()

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

		self.is_recording = False

		# Reset tracking state for next session
		self.last_finalized_len = 0
		self.last_seen_transcription = ""


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
			self.audio_chunk_queue.put(data)

	def _process_wlk_transcription(self, front_data):
		"""
		WLK emits the full accumulated text on every callback.
		With localagreement, text is only ever appended — never revised.
		We just track a cursor (last_finalized_len) and emit any new words.
		"""
		current_text = " ".join(
			seg.text.strip()
			for seg in (front_data.lines or [])
			if hasattr(seg, 'text') and seg.text and seg.text.strip()
		)

		if not current_text or current_text == self.last_seen_transcription:
			return
		self.last_seen_transcription = current_text

		print("[WLK RAW]")
		print(json.dumps(front_data.to_dict(), indent=4, default=str))

		if self.wlk_output_dir:
			now = datetime.now()
			ts = f"{now.year}_{now.month:02d}_{now.day:02d}__{now.hour:02d}_{now.minute:02d}_{now.second:02d}.{now.microsecond // 1000:03d}"
			try:
				with open(os.path.join(self.wlk_output_dir, f"frontdata_{ts}.json"), 'w') as f:
					json.dump(front_data.to_dict(), f, indent=4, default=str)
			except Exception:
				pass

		new_text = current_text[self.last_finalized_len:]
		if not new_text:
			return
		self.last_finalized_len = len(current_text)

		import nltk
		tokens = nltk.word_tokenize(clean_transcription_text(new_text).lower())
		tokens = [t for t in tokens if t.isalnum()]

		with self.transcription_lock:
			for token in tokens:
				node = WordNode(word=token, start_time=datetime.now(), end_time=datetime.now())
				if self.last_node:
					self.last_node.next = node
					node.prev = self.last_node
				self.last_node = node
				self.word_queue.put(node)
				print(f"[WORD] '{token}'")
						
def get_stream(session_id: str) -> WhisperLiveKitWordStream:
	'''
	Gets the word stream for the given session.
	'''
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return WhisperLiveKitWordStream.streams[session_id]


@WhisperLiveKitWordStream.socketio.on('connect')
def handle_connect():
	pass


@WhisperLiveKitWordStream.socketio.on('disconnect')
def handle_disconnect():
	pass


@WhisperLiveKitWordStream.socketio.on('start_listening')
def _start_listening(data: dict) -> Response:
	'''
	Receive the client command to start listening.

	This will establish a connection to WhisperLiveKit
	and start streaming audio for transcription.
	'''
	session_id = data.get('session_id')
	mime_type = data.get("mime_type", "audio/webm")
	get_stream(session_id)._start_listening(mime_type)


@WhisperLiveKitWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict = None) -> Response:
	'''
	Receive the client command to stop listening.
	'''
	session_id = data.get('session_id')
	get_stream(session_id)._stop_listening()


@WhisperLiveKitWordStream.socketio.on("audio_chunk")
def _handle_audio_chunk(data):
	'''
	Receive a live audio chunk from the client microphone.
	Records to file and sends to WhisperLiveKit.
	'''
	session_id = data.get("session_id")
	audio_data = data.get("audio_data")
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
		get_stream(session_id)._start_listening(mime_type)
		return jsonify({"status": "ok"}), 200
	except Exception as e:
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
		get_stream(session_id)._stop_listening()
		return jsonify({"status": "ok"}), 200
	except Exception as e:
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
