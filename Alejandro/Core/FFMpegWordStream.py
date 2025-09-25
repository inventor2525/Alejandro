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
		self.session_id = session_id
		FFmpegWordStream.streams[session_id] = self
		
		self.save_directory = save_directory
		if save_directory:
			os.makedirs(save_directory, exist_ok=True)
		
		self.running = True
		self.is_recording = False
		self.word_queue = Queue()
		
		self.current_audio_path:str = None
		self.current_audio_file:BufferedWriter = None
		self.recording_process:subprocess.Popen[bytes] = None
		
		self.last_node:WordNode = None
		self.start_time:datetime = None
		self.end_time:datetime = None

		self.utterance_lock = threading.Lock()
		self.current_utterance_start_ms: Optional[int] = None
		self.current_utterance_end_ms: Optional[int] = None
		self.last_speech_update: Optional[float] = None
		self.utterance_thread: Optional[threading.Thread] = None
		self.chunk_counter = 0
		
		self.queue_size = 1
		self.padding = 1
	
	@staticmethod
	def init_app(app:Flask):
		FFmpegWordStream.socketio.init_app(app)
		app.register_blueprint(FFmpegWordStream.bp)
	
	def words(self) -> Iterator[WordNode]:
		while self.running:
			try:
				yield self.word_queue.get(block=True, timeout=0.5)
			except Empty as e:
				pass
		return
	
	def close(self):
		'''
		Stops any iterator (or thread iterating it).
		'''
		self._stop_listening()
		self.running = False
		del FFmpegWordStream.streams[self.session_id]
	
	def _start_listening(self, mime_type:str) -> None:
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
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			universal_newlines=False,
		)
		def log_ffmpeg_output(self=self):
			print("Begin logging")
			try:
				while self.recording_process and self.recording_process.poll() is None:
					print("process exists")
					if self.recording_process.stdout:
						stdout = self.recording_process.stdout.readline()
						if stdout:
							print(f"FFmpeg stdout: {stdout}")
					if self.recording_process.stderr:
						stderr = self.recording_process.stderr.readline()
						if stderr:
							print(f"FFmpeg stderr: {stderr}")
					print("looping read logs...")
			except Exception as e:
				print(f'!!!!!!!!!! log failed !!!!!!!!!!\n{e}')
				pass
		from threading import Thread
		Thread(target=log_ffmpeg_output, daemon=True).start()
		self.is_recording = True

	def _stop_listening(self) -> None:
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
			
	def _receive_transcription(self, data:dict):
		text = data.get("text", "")
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

		with self.utterance_lock:
			if self.current_utterance_start_ms is None:
				self.current_utterance_start_ms = data.get("start", 0)
				self.current_utterance_end_ms = data.get("end", 0)
			else:
				if data.get("end", 0) > self.current_utterance_end_ms:
					self.current_utterance_end_ms = data.get("end", 0)
			self.last_speech_update = time.time()

		if not self.utterance_thread or not self.utterance_thread.is_alive():
			self.utterance_thread = threading.Thread(target=self._process_utterances, daemon=True)
			self.utterance_thread.start()

	def _process_utterances(self):
		while self.running:
			time.sleep(0.5)
			start_sec, end_sec, transcribe_block = 0,0,False
			with self.utterance_lock:
				if self.last_speech_update and time.time() - self.last_speech_update > self.queue_size+self.padding:
					start_sec = max(0, self.current_utterance_start_ms / 1000 - self.padding)
					end_sec = self.current_utterance_end_ms / 1000 + self.padding
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
				response_format="json",
				language="en",
				temperature=0.0
			)
			return transcription.text

def get_stream(session_id:str) -> FFmpegWordStream:
	from Alejandro.web.session import get_or_create_session
	get_or_create_session(session_id)
	return FFmpegWordStream.streams[session_id]

@FFmpegWordStream.socketio.on('start_listening')
def _start_listening(data: dict) -> Response:
	session_id = data.get('session_id')
	mime_type = data.get("mime_type", "audio/webm")
	get_stream(session_id)._start_listening(mime_type)

@FFmpegWordStream.socketio.on('stop_listening')
def _stop_listening(data: dict=None) -> Response:
	print(data)
	session_id = data.get('session_id')
	get_stream(session_id)._stop_listening()

@FFmpegWordStream.socketio.on("audio_chunk")
def _handle_audio_chunk(data):
	session_id = data.get("session_id")
	audio_data = data.get("audio_data")
	get_stream(session_id)._handle_audio_chunk(audio_data)

@FFmpegWordStream.bp.route("/new_transcription", methods=["POST"])
def _receive_transcription():
	session_id = request.args.get('session_id')
	word_stream = get_stream(session_id)
	
	while word_stream.is_recording:
		line = request.stream.readline().decode('utf-8').strip()
		if len(line):
			print(f"Received transcription line: '{line}'")
		try:
			data = json.loads(line)
		except:
			data = None
		
		if data:
			word_stream._receive_transcription(data)
	return Response(status=200)

@FFmpegWordStream.socketio.on('manual_transcription')
def handle_manual_transcription(data: dict):
	session_id = data.get('session_id')
	text = data.get('text', '').strip()
	
	if session_id and text:
		word_stream = get_stream(session_id)
		if word_stream:
			word_stream._receive_transcription({'text': text})

@FFmpegWordStream.bp.route('/recorder')
def recorder():
	session_id = request.args.get('session')
	if not session_id:
		return "No session ID provided", 400
	return render_template('recorder.html', session_id=session_id)