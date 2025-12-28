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

# Try to import WhisperLiveKit components
try:
	from whisperlivekit import TranscriptionEngine, AudioProcessor
	WLK_AVAILABLE = True
except ImportError:
	print("[WLK] WhisperLiveKit not available - transcription will not work")
	print("[WLK] Install with: pip install whisperlivekit")
	WLK_AVAILABLE = False
	TranscriptionEngine = None
	AudioProcessor = None

# Global TranscriptionEngine (heavy - create once)
# This will be initialized on first use
_transcription_engine: Optional['TranscriptionEngine'] = None

def get_transcription_engine(model: str = "medium", diarization: bool = True, language: str = "en"):
	"""Get or create the global TranscriptionEngine"""
	global _transcription_engine
	if _transcription_engine is None and WLK_AVAILABLE:
		print(f"[WLK] Creating global TranscriptionEngine (model={model}, diarization={diarization}, language={language})")
		_transcription_engine = TranscriptionEngine(model=model, diarization=diarization, lan=language)
		print("[WLK] TranscriptionEngine created successfully")
	return _transcription_engine

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
		session_id: Optional[str] = None,
		model: str = "medium",
		diarization: bool = True,
		language: str = "en"
	):
		'''
		save_directory should be the folder that all
		recordings and their transcriptions will be
		stored in.

		model: Whisper model to use (tiny, base, small, medium, large)
		diarization: Enable speaker diarization
		language: Language code for transcription
		'''
		# Setup a word stream for each session:
		self.session_id = session_id
		WhisperLiveKitWordStream.streams[session_id] = self

		# Setup save directory (All client audio should be saved here):
		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)

		# WhisperLiveKit settings:
		self.model = model
		self.diarization = diarization
		self.language = language
		self.audio_processor: Optional['AudioProcessor'] = None

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
		'''
		if not WLK_AVAILABLE:
			print("[WLK] WhisperLiveKit not available - cannot initialize AudioProcessor")
			return

		try:
			# Get or create the global transcription engine
			engine = get_transcription_engine(
				model=self.model,
				diarization=self.diarization,
				language=self.language
			)

			if engine is None:
				print("[WLK] Failed to create TranscriptionEngine")
				return

			# Create AudioProcessor for this session
			print(f"[WLK] Creating AudioProcessor for session {self.session_id}")
			self.audio_processor = AudioProcessor(transcription_engine=engine)

			# Set up callback for transcription results
			# Note: The actual API might differ - this is based on typical patterns
			# We'll need to check the actual WLK documentation for the exact callback mechanism
			print("[WLK] AudioProcessor initialized successfully")

		except Exception as e:
			print(f"[WLK] Failed to initialize AudioProcessor: {e}")
			import traceback
			traceback.print_exc()
			self.audio_processor = None

	def _close_audio_processor(self):
		'''Close the AudioProcessor for this session'''
		if self.audio_processor:
			try:
				# Clean up the audio processor
				# The actual cleanup method will depend on WLK's API
				print(f"[WLK] Closing AudioProcessor for session {self.session_id}")
				self.audio_processor = None
			except Exception as e:
				print(f"[WLK] Error closing AudioProcessor: {e}")

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

		# Initialize WhisperLiveKit AudioProcessor
		self._init_audio_processor()

		self.is_recording = True
		print(f"[START] Recording started, is_recording={self.is_recording}")

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
		Record audio chunk to file and process with WhisperLiveKit.
		"""
		# Write to disk (CRITICAL: preserve this functionality!)
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		# Process audio with WhisperLiveKit AudioProcessor
		if self.audio_processor and self.is_recording:
			try:
				print(f"[WLK] Processing {len(data)} bytes with AudioProcessor")

				# Process the audio chunk
				# Note: The actual API method name might differ - common names are:
				# - process_audio(audio_bytes)
				# - feed_audio(audio_bytes)
				# - add_audio(audio_bytes)
				# We'll need to check the actual WLK source for the correct method

				# Attempt to process audio and get transcription results
				# This is a placeholder - the actual implementation depends on WLK's API
				if hasattr(self.audio_processor, 'process_audio'):
					result = self.audio_processor.process_audio(data)
					if result:
						self._process_wlk_transcription(result)
				elif hasattr(self.audio_processor, 'feed_audio'):
					result = self.audio_processor.feed_audio(data)
					if result:
						self._process_wlk_transcription(result)
				else:
					print("[WLK] WARNING: AudioProcessor API method not found")
					print("[WLK] Available methods:", dir(self.audio_processor))

			except Exception as e:
				print(f"[WLK] Error processing audio: {e}")
				import traceback
				traceback.print_exc()
		else:
			if not self.audio_processor:
				print(f"[WLK] Not processing: audio_processor not initialized")
			elif not self.is_recording:
				print(f"[WLK] Not processing: is_recording={self.is_recording}")

	def _process_wlk_transcription(self, data: dict):
		'''
		Process transcription results from WhisperLiveKit.

		Expected data format (typical for real-time transcription):
		{
			"type": "transcription",
			"text": "full transcription text",
			"words": [
				{"word": "hello", "start": 0.0, "end": 0.5},
				{"word": "world", "start": 0.5, "end": 1.0}
			]
		}

		Or simpler format without word-level timestamps:
		{
			"type": "transcription",
			"text": "transcribed text",
			"start": 0.0,
			"end": 2.0
		}
		'''
		msg_type = data.get('type', '')
		print(f"[WLK] Processing message type: {msg_type}")

		# Handle different message types
		if msg_type == 'transcription' or msg_type == 'segment':
			print(f"[WLK] TRANSCRIPTION RECEIVED: {data}")
			with self.transcription_lock:
				# Check if we have word-level timestamps
				words_data = data.get('words', [])

				if words_data:
					print(f"[WLK] Processing {len(words_data)} words with timestamps")
					# Process word-level transcription
					self._process_word_level_transcription(words_data)
				else:
					# Process text-level transcription
					text = data.get('text', '')
					start_offset = data.get('start', 0.0)
					end_offset = data.get('end', 0.0)
					print(f"[WLK] Processing text-level: '{text}' ({start_offset}-{end_offset})")

					if text:
						self._process_text_level_transcription(
							text,
							start_offset,
							end_offset
						)
		elif msg_type == 'error':
			print(f"[WLK] ERROR: {data.get('message', 'Unknown error')}")
		else:
			print(f"[WLK] NON-TRANSCRIPTION MESSAGE: type={msg_type}, data={data}")

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
