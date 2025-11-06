from typing import Optional, Iterator, Dict
from .WordStream import WordStream, WordNode
from flask import Blueprint, jsonify, Response, request, Flask, render_template
from flask_socketio import SocketIO
from io import BufferedWriter
from queue import Queue, Empty
import subprocess
import datetime
import signal
import json
import os
import time
import threading
from groq import Groq

mime_to_config = {
	"audio/webm": ("webm", "matroska", "opus"),
	"audio/ogg": ("ogg", "ogg", "opus"),
	"audio/wav": ("wav", "wav", "pcm_s16le"),
	"audio/mpeg": ("mp3", "mp3", "mp3"),
	"audio/aac": ("aac", "adts", "aac"),
}

class FFmpegWordStream(WordStream):
	bp = Blueprint('FFmpegWordStream', __name__)
	socketio: SocketIO = SocketIO()#cors_allowed_origins="*")
	streams:Dict[str, 'FFmpegWordStream'] = {}
	
	def __init__(self, save_directory:Optional[str], session_id:Optional[str]=None):
		'''
		save_directory should be the folder that all
		recordings and their transcriptions will be
		stored in.
		'''
		# Setup a word stream for each session:
		self.session_id = session_id
		FFmpegWordStream.streams[session_id] = self
		
		# Setup save directory (All client audio should be saved here as a primary feature, for future re-training.):
		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)
		
		# State:
		self._running = True
		'''Used only once to close the client session.'''
		self.is_recording = False
		'''Toggled on start_listening and stop_listening.'''
		self.word_queue = Queue()
		'''All words that we have transcribed but that have not yet been consumed by the 'words' iterator.'''
		
		# For saving & processing the current audio:
		self.current_audio_path:str = None
		self.current_audio_file:BufferedWriter = None
		self.recording_process:subprocess.Popen[bytes] = None
		self.start_time:datetime = None
		self.end_time:datetime = None
		
		# For getting a stream of 'utterances' transcribed
		# using the local model inside ffmpeg so that they
		# can be re-translated on another thread by a larger
		# model:
		self.last_node:WordNode = None
		self.utterance_lock = threading.Lock()
		self.current_utterance_start_ms: Optional[int] = None
		self.current_utterance_end_ms: Optional[int] = None
		self.last_speech_update: Optional[float] = None
		self.utterance_thread: Optional[threading.Thread] = None
		self.chunk_counter = 0
		
		# Settings:
		self.queue_size = 2
		'''How many seconds of audio that will be locally transcribed at a time.'''
		
		self.padding = 1
		'''How much audio (seconds) will be included to the remote (larger model) before and after the local model detects nothing.'''
	
	@staticmethod
	def init_app(app:Flask):
		FFmpegWordStream.socketio.init_app(app)
		app.register_blueprint(FFmpegWordStream.bp)
	
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
			except Empty as e:
				pass
		return
	
	def close(self):
		'''
		Stops any 'self.words' iterator (or thread iterating it).
		'''
		self._stop_listening()
		self._running = False
		del FFmpegWordStream.streams[self.session_id]
	
	def _start_listening(self, mime_type:str) -> None:
		'''
		Start recording client audio chunks to file, 
		and running transcriptions live via ffmpeg locally.
		'''
		self.start_time = datetime.datetime.now()
		timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
	
		self.file_ext = mime_to_config.get(mime_type, ("webm", "matroska", "opus"))[0]
		self.current_audio_path = os.path.join(self.save_directory, f"raw_recording_{timestamp}.{self.file_ext}")
		self.current_audio_file = open(self.current_audio_path, "wb")
		input_format, input_codec = mime_to_config.get(mime_type, ("matroska", "opus"))[1:]

		cmd = [
			"/home/charlie/Projects/ffmpeg_whisper/FFmpeg/ffmpeg",
			"-f", input_format,
			"-c:a", input_codec,
			"-i", "pipe:0",
			"-af", f"pan=mono|c0=c0,highpass=f=200,lowpass=f=3000,whisper=model=/home/charlie/Projects/ffmpeg_whisper/whisper-build/whisper.cpp/models/ggml-tiny.en.bin:language=en:queue={self.queue_size}:destination=http\\\\://127.0.0.1\\\\:5000/new_transcription?session_id={self.session_id}:format=json:vad_model=/home/charlie/Projects/ffmpeg_whisper/whisper-build/whisper.cpp/models/ggml-silero-v5.1.2.bin:vad_threshold=0.7:vad_min_silence_duration=0.5",
			"-f", "null",
			"-"
		]

		self.recording_process = subprocess.Popen(
			cmd,
			stdin=subprocess.PIPE,
			universal_newlines=False,
		)
		self.is_recording = True

	def _stop_listening(self) -> None:
		'''
		Shut down ffmpeg and name the finished audio recording.
		'''
		self.end_time = datetime.datetime.now()
		
		if self.current_audio_file:
			self.current_audio_file.close()
			
		if self.recording_process:
			if self.recording_process.stdin:
				self.recording_process.stdin.close()
			self.recording_process.send_signal(signal.SIGINT)
			self.recording_process.wait()
		
		start_str = self.start_time.strftime("%Y%m%d_%H%M%S")
		end_str = self.end_time.strftime("%Y%m%d_%H%M%S")
		new_raw = os.path.join(self.save_directory, f"recording_{start_str}__{end_str}.{self.file_ext}")
		os.rename(self.current_audio_path, new_raw)
		
		self.is_recording = False
	
	def _handle_audio_chunk(self, data: bytes):
		"""Append chunk to raw file and pipe to FFmpeg."""
		if self.current_audio_file and not self.current_audio_file.closed:
			self.current_audio_file.write(data)
			self.current_audio_file.flush()

		if self.recording_process and self.recording_process.poll() is None and self.recording_process.stdin:
			self.recording_process.stdin.write(data)
			self.recording_process.stdin.flush()
	
	def add_text_to_queue(self, text:str):
		if text:
			nodes = self.process_text(text)
			now = datetime.datetime.now()
			for node in nodes:
				node.start_time = now
				node.end_time = now
			if nodes:
				if self.last_node:
					self.last_node.next = nodes[0]
					nodes[0].prev = self.last_node
				self.last_node = nodes[-1]
				for node in nodes:
					self.word_queue.put(node)
	
	def _process_local_transcription(self, text:str, start:int, end:int):
		self.add_text_to_queue(text)
		with self.utterance_lock:
			if self.current_utterance_start_ms is None:
				self.current_utterance_start_ms = start
				self.current_utterance_end_ms = end
			else:
				if end > self.current_utterance_end_ms:
					self.current_utterance_end_ms = end
			self.last_speech_update = time.time()
		
		# Start transcribing any utterances using a smarter model in the background:
		if not self.utterance_thread or not self.utterance_thread.is_alive():
			self.utterance_thread = threading.Thread(target=self._process_utterances, daemon=True)
			self.utterance_thread.start()

	def _process_utterances(self):
		while self._running:
			# Wait for some period so we can at least get 'an utterance':
			time.sleep(0.1)
			start_sec, end_sec, transcribe_block = 0,0,False
			with self.utterance_lock:
				# If it's been at least 'padding' seconds since the last time uttering was detected using the local model:
				if self.last_speech_update and time.time() - self.last_speech_update > self.queue_size+self.padding:
					# Get the start and end time of this utterance:
					start_sec = max(0, self.current_utterance_start_ms / 1000 - self.padding)
					end_sec = self.current_utterance_end_ms / 1000 + self.padding
					
					# Clear state for next utterance to be collected:
					self.current_utterance_start_ms = None
					self.current_utterance_end_ms = None
					self.last_speech_update = None
					transcribe_block = True
			
			if transcribe_block:
				chunk_path = self.current_audio_path + f"_chunk{self.chunk_counter}.m4a"
				self.chunk_counter += 1
				self._extract_audio_chunk(start_sec, end_sec - start_sec, chunk_path)

				groq_text = self._transcribe_with_groq(chunk_path)
				print(f"Groq transcription: {groq_text}")


	def _extract_audio_chunk(self, start, duration, output_path):
		cmd = [
			"/home/charlie/Projects/ffmpeg_whisper/FFmpeg/ffmpeg",
			"-i", self.current_audio_path,
			"-ss", str(start),
			"-t", str(duration),
			"-af", "pan=mono|c0=c0",
			"-hide_banner",
			"-loglevel", "error",
			"-nostats",
			"-c:a", "aac",
			"-y",
			output_path
		]
		subprocess.run(cmd, check=True)

	def _transcribe_with_groq(self, filename):
		client = Groq()
		with open(filename, "rb") as file:
			transcription = client.audio.transcriptions.create(
				file=(os.path.basename(filename), file.read()),
				model="whisper-large-v3",
				response_format="verbose_json",
				language="en",
				temperature=0.5,
				timestamp_granularities=['word'],
				prompt="Utterances should [um], include fillers. Maybe [uh] too: They should always be punctuated, even when it's not really a sentence. Things said, don't always [um]... You know? Have to be sentences right? I did always like computers... When they... When they didn't just speak in all lower case words without marks; I much prefer it when they do! I also, you know, you know I much prefer when they verbatim transcribe me. Even if I say something, maybe I say something, multiple times, it should do that too!"
			)
			print(json.dumps(transcription.to_dict(),indent=4))
			return transcription.text

def get_stream(session_id:str) -> FFmpegWordStream:
	'''
	Gets the word stream for the given session.
	'''
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return FFmpegWordStream.streams[session_id]

@FFmpegWordStream.socketio.on('start_listening')
def _start_listening(data: dict) -> Response:
	'''
	Receive the client command to start listening.
	
	This will spin up an ffmpeg instance that will
	receive audio chunks from the client, and automatically
	attempt to transcribe them, then passing those
	transcribed chunks to _receive_transcription.
	'''
	session_id = data.get('session_id')
	mime_type = data.get("mime_type", "audio/webm")
	get_stream(session_id)._start_listening(mime_type)

@FFmpegWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict=None) -> Response:
	'''
	Receive the client command to stop listening.
	'''
	session_id = data.get('session_id')
	get_stream(session_id)._stop_listening()

@FFmpegWordStream.socketio.on("audio_chunk")
def _handle_audio_chunk(data):
	'''
	Receive a live audio chunk from the client microphone.
	'''
	session_id = data.get("session_id")
	audio_data = data.get("audio_data")
	get_stream(session_id)._handle_audio_chunk(audio_data)

@FFmpegWordStream.bp.route("/new_transcription", methods=["POST"])
def _receive_transcription():
	'''
	Receive streaming transcriptions from the live transcription
	model being run inside ffmpeg.
	
	These transcriptions are usually poor and do not contain
	word level time stamps.
	'''
	session_id = request.args.get('session_id')
	word_stream = get_stream(session_id)
	
	while word_stream.is_recording:
		line = request.stream.readline().decode('utf-8').strip()
		if len(line):
			print(f"Received transcription line: '{line}'")
		try:
			data:dict = json.loads(line)
		except:
			data = None
		
		if data:
			word_stream._process_local_transcription(
				data.get('text',''),
				data.get('start',0),
				data.get('end',  0)
			)
	return Response(status=200)

@FFmpegWordStream.socketio.on('manual_text_entry')
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
			word_stream.add_text_to_queue(text)

@FFmpegWordStream.bp.route('/recorder')
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

# Format of raw transcription json:
# {"start":894340,"end":896340,"text":">> Hello, everybody."}

# {"start":896340,"end":897580,"text":"that are helping you hear me now."}

# {  
#     "text": " Hello computer, how can you hear me now?",
#     "task": "transcribe",
#     "language": "English",
#     "duration": 5.24,
#     "words": [
#         {
#             "word": "Hello",
#             "start": 0,
#             "end": 2.8
#         },
#         {
#             "word": "computer,",
#             "start": 2.8,
#             "end": 3.14
#         },
#         {
#             "word": "how",
#             "start": 3.14,
#             "end": 3.28
#         },
#         {
#             "word": "can",
#             "start": 3.28,
#             "end": 3.4
#         },
#         {
#             "word": "you",
#             "start": 3.4,
#             "end": 3.48
#         },
#         {
#             "word": "hear",
#             "start": 3.48,
#             "end": 3.58
#         },
#         {
#             "word": "me",
#             "start": 3.58,
#             "end": 3.7
#         },
#         {
#             "word": "now?",
#             "start": 3.7,
#             "end": 3.92
#         }
#     ],
#     "segments": null,
#     "x_groq": {
#         "id": "req_01k6126z9kes49gdz2z74xawbx"
#     }
# }