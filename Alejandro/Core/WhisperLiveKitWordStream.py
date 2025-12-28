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
import websocket
import base64

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
		wlk_host: str = "localhost",
		wlk_port: int = 8000,
		language: str = "en"
	):
		'''
		save_directory should be the folder that all
		recordings and their transcriptions will be
		stored in.

		wlk_host: WhisperLiveKit WebSocket server host
		wlk_port: WhisperLiveKit WebSocket server port
		language: Language code for transcription
		'''
		# Setup a word stream for each session:
		self.session_id = session_id
		WhisperLiveKitWordStream.streams[session_id] = self

		# Setup save directory (All client audio should be saved here):
		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)

		# WhisperLiveKit connection settings:
		self.wlk_host = wlk_host
		self.wlk_port = wlk_port
		self.language = language
		self.wlk_ws: Optional[websocket.WebSocketApp] = None
		self.wlk_thread: Optional[threading.Thread] = None

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

	def _connect_to_wlk(self):
		'''
		Establish WebSocket connection to WhisperLiveKit server.
		'''
		try:
			wlk_url = f"ws://{self.wlk_host}:{self.wlk_port}"
			print(f"Connecting to WLK at {wlk_url}")

			def on_message(ws, message):
				'''Handle transcription results from WhisperLiveKit'''
				print(f"WLK message: {message}")
				try:
					data = json.loads(message)
					self._process_wlk_transcription(data)
				except json.JSONDecodeError as e:
					print(f"Error decoding WLK message: {e}")
				except Exception as e:
					print(f"Error processing WLK transcription: {e}")

			def on_error(ws, error):
				print(f"WLK error: {error}")

			def on_close(ws, close_status_code, close_msg):
				print(f"WLK closed: {close_status_code} - {close_msg}")

			def on_open(ws):
				print("WLK connection opened")
				try:
					config = {
						"type": "config",
						"language": self.language,
						"task": "transcribe"
					}
					ws.send(json.dumps(config))
					print(f"Sent config: {config}")
				except Exception as e:
					print(f"Error sending config: {e}")

			self.wlk_ws = websocket.WebSocketApp(
				wlk_url,
				on_message=on_message,
				on_error=on_error,
				on_close=on_close,
				on_open=on_open
			)

			self.wlk_thread = threading.Thread(
				target=self.wlk_ws.run_forever,
				daemon=True
			)
			self.wlk_thread.start()
		except Exception as e:
			print(f"Failed to connect to WLK: {e}")
			self.wlk_ws = None
			self.wlk_thread = None

	def _disconnect_from_wlk(self):
		'''Close WhisperLiveKit WebSocket connection'''
		try:
			if self.wlk_ws:
				self.wlk_ws.close()
		except:
			pass
		finally:
			self.wlk_ws = None

		try:
			if self.wlk_thread:
				self.wlk_thread.join(timeout=1)
		except:
			pass
		finally:
			self.wlk_thread = None

	def _start_listening(self, mime_type: str) -> None:
		'''
		Start recording client audio chunks to file
		and establish connection to WhisperLiveKit.
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

		# Connect to WhisperLiveKit
		self._connect_to_wlk()

		self.is_recording = True
		print(f"[START] Recording started, is_recording={self.is_recording}")

	def _stop_listening(self) -> None:
		'''
		Disconnect from WhisperLiveKit and finalize audio recording.
		'''
		print(f"[STOP] Stopping recording...")
		self.end_time = datetime.now()

		# Close audio file
		if self.current_audio_file:
			self.current_audio_file.close()
			print(f"[FILE] Closed audio file")

		# Disconnect from WhisperLiveKit
		self._disconnect_from_wlk()

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
		Record audio chunk to file and send to WhisperLiveKit.
		"""
		# Write to disk (CRITICAL: preserve this functionality!)
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		# Send to WhisperLiveKit for transcription
		if self.wlk_ws and self.is_recording:
			try:
				print(f"Sending {len(data)} bytes to WLK")
				# Encode audio data as base64 for JSON transmission
				audio_b64 = base64.b64encode(data).decode('utf-8')
				message = {
					"type": "audio",
					"data": audio_b64
				}
				self.wlk_ws.send(json.dumps(message))
			except Exception as e:
				print(f"Error sending audio to WLK: {e}")
		else:
			print(f"Not sending audio: wlk_ws={self.wlk_ws is not None}, is_recording={self.is_recording}")

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
