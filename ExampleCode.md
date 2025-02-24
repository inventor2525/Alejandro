# This is an example of what will be the core part of the functionality I was talking about:

AbstractAI/web/functions.py
```python
from typing import Type, Dict, Optional, Union
from models import Screen

# Global registry of active screens
active_screens: Dict[Type[Screen], Screen] = {}

def navigate(target: Union[Type[Screen], Screen], **kwargs) -> dict:
    """
    Navigate to a screen. Can take either:
    - A Screen type (will reuse existing instance or create new one)
    - A Screen instance (will navigate directly to it)
    
    Returns navigation response dict
    """
    if isinstance(target, type):
        # If we got a screen type, get/create instance
        if target not in active_screens:
            active_screens[target] = target(**kwargs)
        screen = active_screens[target]
    else:
        # If we got a screen instance, use it directly
        screen = target
        active_screens[type(screen)] = screen
        
    from app import screen_stack
    screen_stack.push(screen)
    
    return {
        "navigate": type(screen).__name__.lower(),
        "force": True  # Always force reload
    }

def go_back() -> dict:
    """Pop current screen and return to previous"""
    from app import screen_stack
    
    if len(screen_stack._stack) > 1:
        popped = screen_stack.pop()
        current = screen_stack.current
        print(f"Going back: popped {type(popped).__name__}, current is now {type(current).__name__}")
        print(f"Screen stack is now: {[type(s).__name__ for s in screen_stack._stack]}")
        return {
            "navigate": type(current).__name__.lower(),
            "force": True
        }
    
    print("Cannot go back further - at root screen")
    print(f"Screen stack is: {[type(s).__name__ for s in screen_stack._stack]}")
    return {
        "navigate": "welcome",
        "force": True
    }
```
functions.py

AbstractAI/web/models.py
```python
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Union, Any, Type
from enum import Enum
from datetime import datetime
from AbstractAI.Model.Converse.Conversation import Conversation

# Map both written numbers and digits to standardized form
NUMBER_MAP = {
    'zero': '0', '0': '0',
    'one': '1', '1': '1',
    'two': '2', '2': '2',
    'three': '3', '3': '3', 
    'four': '4', '4': '4',
    'five': '5', '5': '5',
    'six': '6', '6': '6',
    'seven': '7', '7': '7',
    'eight': '8', '8': '8',
    'nine': '9', '9': '9',
    'ten': '10', '10': '10'
}

@dataclass
class WordNode:
    """A node in the linked list of words from transcription"""
    word: str
    timestamp: datetime
    prev: Optional['WordNode'] = None
    next: Optional['WordNode'] = None
    
    def __str__(self):
        return self.word

@dataclass
class Control:
    id: str
    text: str  # Primary text shown on button
    keyphrases: List[str] = field(default_factory=list)  # Alternative phrases that trigger this control
    action: Callable = field(default_factory=lambda: lambda: None)  # Function to call when activated
    
    def validate_word(self, word_node: WordNode) -> bool:
        """
        Check if this word completes any of our key phrases by looking backwards
        """
        print(f"Validating word: {word_node.word} at {word_node.timestamp}")
        
        def check_phrase(phrase: str) -> bool:
            words = phrase.lower().split()
            current = word_node
            
            for target in reversed(words):
                current_word = current.word.lower() if current else None
                
                if not current or current_word != target:
                    if current and current_word in NUMBER_MAP and target in NUMBER_MAP:
                        if NUMBER_MAP[current_word] != NUMBER_MAP[target]:
                            return False
                    else:
                        return False
                current = current.prev
            return True
            
        return check_phrase(self.text) or any(check_phrase(phrase) for phrase in self.keyphrases)

@dataclass 
class Screen:
    """
    Base screen class representing a distinct view in the application.
    Each screen has its own template, title, and set of controls.
    
    Specific screen types (Welcome, Terminal, etc.) inherit from this
    to provide their unique functionality while maintaining a consistent
    interface for the navigation system.
    
    The screen itself represents a specific instance of a view - for example,
    a ConversationScreen instance represents viewing a specific conversation,
    not just the generic concept of viewing conversations.
    """
    title: str
    template: str
    controls: List[Control] = field(default_factory=list)
    
    def __eq__(self, other: 'Screen') -> bool:
        if not isinstance(other, type(self)):
            return False
        return type(self) == type(other)
    
    def get_template_data(self) -> dict:
        """Get any additional template data needed for rendering"""
        return {}
    
    def handle_control(self, control_id: str) -> Optional[dict]:
        """Handle a control being triggered"""
        for control in self.controls:
            if control.id == control_id:
                return control.action()
        return None

    def on_enter(self) -> None:
        """Called when this screen becomes active"""
        pass
        
    def on_exit(self) -> None:
        """Called when navigating away from this screen"""
        pass

@dataclass
class WelcomeScreen(Screen):
    def __init__(self):
        from functions import navigate
        super().__init__(
            title="Welcome",
            template="welcome.html",
            controls=[
                Control(
                    id="activate",
                    text="Hey Alejandro",
                    keyphrases=["hey alejandro", "yo alejandro", "what's up alejandro", 
                              "hello alejandro", "hail alejandro"],
                    action=lambda: navigate(MainScreen)
                )
            ]
        )

@dataclass
class MainScreen(Screen):
    def __init__(self):
        from functions import navigate, go_back
        super().__init__(
            title="Main Menu",
            template="base.html",
            controls=[
                Control(id="conversation", text="Conversations", 
                       keyphrases=["conversation", "conversations", "converse"],
                       action=lambda: navigate(ConversationListScreen)),
                Control(id="terminal", text="Terminal",
                       keyphrases=["terminal", "console", "shell", "command line"],
                       action=lambda: navigate(TerminalScreen)),
                Control(id="cancel", text="Cancel",
                       keyphrases=["cancel", "escape", "back", "never mind"],
                       action=go_back)
            ]
        )

@dataclass
class ConversationListScreen(Screen):
    def __init__(self):
        from functions import go_back
        super().__init__(
            title="Conversations",
            template="conversation_list.html",
            controls=[
                Control(id="cancel", text="Cancel",
                       keyphrases=["cancel", "escape", "back", "never mind"],
                       action=go_back)
            ]
        )
    
    def get_template_data(self) -> dict:
        from AbstractAI.AppContext import AppContext
        return {
            "conversations": AppContext.engine.query(Conversation).all()
        }

@dataclass
class ConversationScreen(Screen):
    conversation: Conversation = field(default=None)
    
    def __init__(self, conversation: Conversation):
        super().__init__(
            title=f"Conversation - {conversation.name}",
            template="conversation.html",
            controls=[
                Control(id="cancel", text="Cancel",
                       keyphrases=["cancel", "escape", "back", "never mind"]),
                Control(id="send", text="Send Message",
                       keyphrases=["send message", "send", "submit"])
            ]
        )
        self.conversation = conversation
    
    def __eq__(self, other: 'ConversationScreen') -> bool:
        if not isinstance(other, ConversationScreen):
            return False
        return self.conversation.auto_id == other.conversation.auto_id
    
    def get_template_data(self) -> dict:
        from AbstractAI.Model.Converse.MessageSources.ModelSource import ModelSource
        messages = []
        for msg in self.conversation.message_sequence:
            source = msg.get_source(ModelSource)
            messages.append({
                'content': msg.content,
                'role': str(msg.role),
                'is_model': source is not None,
                'date': msg.date_created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(msg, 'date_created') else None,
                'model_name': source.settings.user_model_name if source and source.settings else None
            })
        return {
            "conversation": self.conversation,
            "messages": messages
        }

@dataclass
class TerminalScreen(Screen):
    def __init__(self):
        from functions import go_back
        super().__init__(
            title="Terminal",
            template="terminal.html",
            controls=[
                Control(id="cancel", text="Cancel",
                       keyphrases=["cancel", "escape", "back", "never mind"],
                       action=go_back)
            ]
        )

class ScreenStack:
    """
    Manages navigation history for the application.
    
    The ScreenStack maintains the history of screens the user has visited,
    enabling back-button functionality. It is not a storage of all screens
    that exist, but rather tracks the path the user has taken through the
    application.
    
    The stack always maintains at least one screen (the welcome screen)
    and handles the lifecycle events (on_enter/on_exit) of screens
    as they are pushed and popped during navigation.
    """
    def __init__(self, welcome_screen: Screen):
        self._stack: List[Screen] = [welcome_screen]
        welcome_screen.on_enter()
        
    def push(self, screen: Screen) -> None:
        if not self._stack or screen != self._stack[-1]:
            if self._stack:
                self._stack[-1].on_exit()
            self._stack.append(screen)
            screen.on_enter()
            print(f"Screen stack after push: {[type(s).__name__ for s in self._stack]}")
        
    def pop(self) -> Screen:
        if len(self._stack) > 1:
            popped = self._stack.pop()
            popped.on_exit()
            self._stack[-1].on_enter()
            print(f"Screen stack after pop: {[type(s).__name__ for s in self._stack]}")
            return popped
        return self._stack[0]  # Return welcome screen
        
    @property
    def current(self) -> Screen:
        return self._stack[-1]
```
models.py

AbstractAI/web/app.py
```python
from flask import Flask, render_template, jsonify, request, Response, url_for
from AbstractAI.Model.Converse.MessageSources.ModelSource import ModelSource
from AbstractAI.Helpers.TerminalClient import Terminal, TerminalFLASKIFY
import requests
import json
from AbstractAI.ApplicationCore import *
import threading
import queue
import os
from datetime import datetime
from typing import Optional, List, Dict, Type
import nltk
import time
from models import (
    Screen, Control, WordNode, ScreenStack,
    WelcomeScreen, MainScreen, ConversationScreen,
    ConversationListScreen, TerminalScreen
)
from functions import navigate, go_back

app = Flask(__name__)
transcription_queue = queue.Queue()
action_queue = queue.Queue()
core = None

def init_core():
    global core
    if core is None:
        core = ApplicationCore("/home/charlie/Documents/AbstractAI")

# Initialize screen stack with welcome screen


# Initialize terminal client
TerminalFLASKIFY.make_client('localhost', 7788)
terminal = None
def init_terminal():
    global terminal
    if terminal is None:
        terminal = Terminal("Web Terminal")

# Track active screens for reuse
active_screens = {}


@app.route('/')
@app.route('/conversation/<string:conv_id>')
@app.route('/<path:screen_id>')
def index(screen_id=None, conv_id=None):
    # Initialize app if needed
    init_app()
    
    if screen_id == 'favicon.ico':
        return '', 204
    
    # Handle conversation routes
    if conv_id:
        try:
            conversation = AppContext.engine.query(Conversation).filter_by_id(conv_id)
            if conversation:
                screen = ConversationScreen(conversation)
                if not isinstance(screen_stack.current, ConversationScreen) or screen_stack.current.conversation.auto_id != conv_id:
                    screen_stack.push(screen)
            else:
                screen = ConversationListScreen()
                screen_stack.push(screen)
                return render_template(screen.template, screen=screen, error=f"Conversation not found: {conv_id}", **screen.get_template_data())
        except Exception as e:
            print(f"Error loading conversation: {str(e)}")
            screen = ConversationListScreen()
            screen_stack.push(screen)
            return render_template(screen.template, screen=screen, error=str(e), **screen.get_template_data())
    
    # Handle screen_id navigation
    elif screen_id:
        screen = None
        if screen_id == "terminal":
            screen = TerminalScreen()
        elif screen_id == "conversations":
            screen = ConversationListScreen()
        elif screen_id == "main" or screen_id == "mainscreen":
            screen = MainScreen()
            
        if screen:
            screen_stack.push(screen)
    
    # Render current screen
    current = screen_stack.current
    return render_template(current.template, screen=current, **current.get_template_data())

@app.route('/screen/<screen_id>')
def get_screen(screen_id):
    screen = None
    if screen_id == "terminal":
        screen = TerminalScreen()
    elif screen_id == "conversations":
        screen = ConversationListScreen()
    elif screen_id == "main":
        screen = MainScreen()
    elif screen_id.startswith("conversation/"):
        try:
            conv_id = screen_id.split("conversation/")[1]
            conversation = AppContext.engine.query(Conversation).filter_by_id(conv_id)
            if conversation:
                screen = ConversationScreen(conversation)
        except Exception as e:
            print(f"Error creating conversation screen: {e}")
            return jsonify({"error": str(e)}), 404

    if screen:
        return jsonify({
            "screen": {
                "title": screen.title,
                "controls": [
                    {
                        "id": c.id,
                        "text": c.text,
                        "keyphrases": c.keyphrases
                    } for c in screen.controls
                ]
            }
        })
    return jsonify({"error": "Screen not found"}), 404

@app.route('/control/<control_id>', methods=['POST'])
def trigger_control(control_id):
    # Get message input if present
    message = request.form.get('messageInput', '')
    
    # Get current screen and handle control
    current_screen = screen_stack.current
    print(f"Triggering control {control_id} for screen {type(current_screen).__name__}")
    
    # Special handling for send message in conversation
    if control_id == 'send' and isinstance(current_screen, ConversationScreen):
        if message.strip():
            current_screen.conversation + (message, Role.User())
            return jsonify({
                "result": "Message sent",
                "navigate": f"conversation/{current_screen.conversation.auto_id}",
                "force": True
            })
        return jsonify({"error": "No message to send"}), 400
    
    # Handle cancel specially to ensure proper navigation
    if control_id == 'cancel':
        return jsonify(go_back())
    
    # Handle other controls
    result = current_screen.handle_control(control_id)
    if result:
        return jsonify(result)
    
    return jsonify({"error": "Control not found"}), 404

@app.route('/get_transcription')
def get_transcription():
    try:
        transcription = transcription_queue.get_nowait()
        if isinstance(transcription, str):
            return jsonify({"text": transcription})
        return jsonify({"text": ""})
    except queue.Empty:
        return jsonify({"text": ""})

def voice_control_thread():
    # Wait for core to be initialized
    while core is None:
        time.sleep(0.1)
        
    try:
        # Track the last word node for linking
        last_word: Optional[WordNode] = None
        
        # Use screen stack for current screen
        global screen_stack
        
        for transcription in core.transcribe_live():
            # Print raw transcription data
            print(f"Raw transcription: {transcription}")
            
            # Send full transcription text to UI
            transcription_queue.put(transcription.text)
            
            def tokenize_text(text: str) -> List[str]:
                """Split text into words, preserving numbers but removing punctuation"""
                # Tokenize using NLTK
                tokens = nltk.word_tokenize(text.lower())
                
                # Keep alphanumeric tokens (words and numbers)
                tokens = [token for token in tokens if token.isalnum()]
                
                return tokens

            # Process words for control validation
            words = tokenize_text(transcription.text)
            timestamp = datetime.now()  # TODO: Get actual word timestamps
            
            # Create word nodes
            for word in words:
                word_node = WordNode(word=word, timestamp=timestamp)
                
                # Link nodes
                if last_word:
                    last_word.next = word_node
                    word_node.prev = last_word
                last_word = word_node
                
                # Get current screen and check its controls
                current_screen = screen_stack.current
                for control in current_screen.controls:
                    if control.validate_word(word_node):
                        print(f"Voice activated control: {control.text}")
                        result = control.action()
                        if isinstance(result, dict):
                            if "navigate" in result:
                                # Don't push if it's a back navigation or if we're already on that screen
                                if not (control.id == "cancel" and control.text == "Cancel"):
                                    if result["navigate"] != screen_stack.current:
                                        screen_stack.push(result["navigate"])
                            action_queue.put(result)
                        else:
                            action_queue.put({"action_result": result})
                        break  # Stop checking other controls after one is activated
                    
    except KeyboardInterrupt:
        print("Stopping transcription...")

def start_voice_control():
    thread = threading.Thread(target=voice_control_thread)
    thread.daemon = True
    thread.start()
    return thread

def event_stream():
    while True:
        try:
            # Check for transcription
            try:
                transcription = transcription_queue.get_nowait()
                yield f"data: {json.dumps({'text': transcription})}\n\n"
                # Flush the stream to ensure immediate delivery
                yield ": keepalive\n\n"
            except queue.Empty:
                pass
                
            # Check for actions
            try:
                action = action_queue.get_nowait()
                # Send navigation events immediately with flush
                yield f"data: {json.dumps(action)}\n\n"
                yield ": keepalive\n\n"
            except queue.Empty:
                # Send periodic keepalive to maintain connection
                yield ": keepalive\n\n"
                
            time.sleep(0.1)  # Prevent busy-waiting
                
        except GeneratorExit:
            break

@app.route('/stream')
def stream():
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/terminal/screen')
def terminal_screen():
    try:
        init_terminal()
        return jsonify(terminal.getScreenDump())
    except requests.exceptions.ConnectionError:
        return jsonify({
            "raw_text": "Terminal server not running. Please start the terminal server first.",
            "color_json": {"colors": [], "cursor": {"x": 0, "y": 0}},
            "cursor_position": {"x": 0, "y": 0}
        })

@app.route('/terminal/input', methods=['POST'])
def terminal_input():
    try:
        init_terminal()
        data = request.json.get('input', '')
        terminal.send_string(data)
        return jsonify({"status": "ok"})
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "message": "Terminal server not running"})

voice_thread = None
_initialized = False

def init_app():
    global voice_thread, core, screen_stack, _initialized
    if not _initialized:
        init_core()
        welcome_screen = WelcomeScreen()
        screen_stack = ScreenStack(welcome_screen)
        voice_thread = start_voice_control()
        _initialized = True

if __name__ == '__main__':
    @app.before_request
    def before_first_request():
        init_app()
    app.run(debug=False, threaded=True)  # Disable debug mode to prevent double init
```
app.py

# Under the hood, it was using this (below)... but for now I want you to replace this with the abstract interface for voice and llm that I mentioned
AbstractAI/ApplicationCore.py
```python
# Setup StopWatch (for application timing):
from AbstractAI.Helpers.Stopwatch import Stopwatch, SafeStopwatch
Stopwatch.singleton = Stopwatch(should_log=True, log_statistics=False)
stopwatch = Stopwatch.singleton

SafeStopwatch.singleton = SafeStopwatch(should_log=True, log_statistics=False)
safe_stopwatch = SafeStopwatch.singleton

# Track import times:
stopwatch("AbstractAI App Core Init")
stopwatch.new_scope()

stopwatch("Basics")
import json
from enum import Enum
from pydub import AudioSegment
from datetime import datetime
from copy import deepcopy
import argparse
import shutil
import os

stopwatch("nltk")
import nltk
from nltk.tokenize import word_tokenize
nltk.download('punkt')

stopwatch("ClassyFlaskDB")
from ClassyFlaskDB.DefaultModel import *
from ClassyFlaskDB.new.AudioTranscoder import AudioTranscoder
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine

stopwatch("Helpers")
from AbstractAI.Helpers.ScopeParams import *
from AbstractAI.Helpers.Signal import Signal, LazySignal
from AbstractAI.Helpers.Jobs import *

stopwatch("LLMSettings")
from AbstractAI.Model.Settings.LLMSettings import *
llm_settings_types = LLMSettings.load_subclasses()

stopwatch("Conversation Model")
from AbstractAI.Model.Converse import *

stopwatch("TTS Settings")
from AbstractAI.Model.Settings.STT_Settings import *

stopwatch("Artifacts")
from AbstractAI.Model.Artifacts import TextArtifact, TextArtifacts, TextFileArtifact

stopwatch("Conversable")
from AbstractAI.Conversable import *
from AbstractAI.LLMs.LLM import LLM
from AbstractAI.Automation.Agent import Agent, AgentConfig
from AbstractAI.LLMs.LLM_Helpers import ResponseObject, LLMParams, LLMJob

stopwatch("Audio IO")
from AbstractAI.Helpers.AudioPlayer import AudioPlayer
from AbstractAI.Helpers.AudioRecorder import AudioRecorder

stopwatch.start("Speech to Text")
from AbstractAI.SpeechToText.Transcriber import Transcriber, Transcription, TranscriptionJob
from AbstractAI.SpeechToText.VAD import VAD, VADSettings
from AbstractAI.SpeechToText.TranscriptionIterator import TranscriptionIterator
stopwatch.stop("Speech to Text")

stopwatch("Text to Speech")
from AbstractAI.TextToSpeech.TTS import TTSJob
from AbstractAI.TextToSpeech.OpenAI_TTS import OpenAI_TTS, OpenAI_TTS_Settings
from AbstractAI.TextToSpeech.Kokoro_TTS import Kokoro_TTS, Kokoro_TTS_Settings

stopwatch("Context")
from AbstractAI.AppContext import AppContext

stopwatch("Application")
T = TypeVar("T")

@dataclass
class ApplicationCore:
	#######################
	#      Config         #
	#######################
	storage_location: str
	# The un-versioned root directory all application data will be stored in
	
	db_version: str = "v3"
	# Current db version
	
	prev_compatible_db_versions: List[str] = default([])
	# Previous versions of the db that are compatible to load with this one.
	
	#######################
	#       State         #
	#######################
	_settings: List[Tuple[Object, Optional[Callable[[],None]]]] = field(default_factory=list, init=False)
	# All settings we will save when calling 'save settings'
	
	_llm_cache:Dict[str, LLMSettings] = field(default_factory=dict, init=False)
	# Mapping for all LLMs based on 'user model name'
	
	#######################
	#      Signals        #
	#######################
	transcription_completed: Signal[[Transcription],None] = Signal[[Transcription],None].field()
	
	def __post_init__(self) -> None:
		stopwatch("AIApplication.init")
		stopwatch.new_scope()
		
		# Get storage locations:
		stopwatch("Path generation")
		if self.storage_location.endswith(".db"):
			self.storage_location = self.storage_location[:-3]
		AppContext.storage_location = self.storage_location
		
		files_path = os.path.join(AppContext.storage_location, "files")
		os.makedirs(files_path, exist_ok=True)
		
		db_path = os.path.join(AppContext.storage_location, self.db_version, "chat.db")
		os.makedirs(os.path.join(AppContext.storage_location, self.db_version), exist_ok=True)
		
		# Migrate old db if needed (and possible):
		if not os.path.exists(db_path):
			stopwatch("DB version migrate")
			for version in self.prev_compatible_db_versions:
				old_db_path = os.path.join(AppContext.storage_location, version, "chat.db")
				if os.path.exists(old_db_path):
					shutil.copyfile(old_db_path, db_path)
		
		# Load/Create & link the database to model classes:
		stopwatch("DB startup")
		AppContext.engine = SQLStorageEngine(f"sqlite:///{db_path}", DATA, files_dir=files_path)
		
		# Load all settings:
		stopwatch("Query Settings")
		self.llmConfigs = self.query_db(LLMConfigs, as_setting=True)
		self.vad_settings = self.query_db(VADSettings, as_setting=True)
		self.stt_settings = self.query_db(STT_Settings_v1, as_setting=True)
		self.speech_settings = self.query_db(OpenAI_TTS_Settings, as_setting=True)
		self.local_speech_settings = self.query_db(Kokoro_TTS_Settings, as_setting=True)
		
		# Create User Source:
		AppContext.user_source = UserSource() | CallerInfo.catch([0])
		
		# Load conversations:
		stopwatch("Load Conversations")
		self.conversations = ConversationCollection.all_from_engine(AppContext.engine)
		
		# Start up audio IO:
		self.audio_recorder = AudioRecorder()
		self.audio_player = AudioPlayer()
		
		# Create Transcriber:
		stopwatch("Transcriber startup")
		self.transcriber = Transcriber(self.stt_settings)

		# Create Voice Activity Detector:
		#TODO: VAD (with offline mode):
		stopwatch("Voice Activity Detector startup")
		self.vad = VAD(self.vad_settings, self.audio_recorder)
		
		# Setup Text to Speech:
		stopwatch("Text to Speech startup")
		self.tts = OpenAI_TTS(self.speech_settings, callback=self.text_to_speech_callback)
		self.local_tts = Kokoro_TTS(self.local_speech_settings, callback=self.text_to_speech_callback)
		
		# Load any previously un-completed jobs:
		stopwatch("Query Jobs")
		AppContext.jobs = self.query_db(Jobs)
		AppContext.jobs.changed.connect(self.save_jobs)
		AppContext.jobs.should_save_job.connect(self._save_job)
		
		# Job registration:
		Jobs.register("Transcribe", self.transcription_work, self.transcription_callback)
		
		# Start processing jobs:
		stopwatch("Start Jobs")
		AppContext.jobs.start()
		
		stopwatch.end_scope() #AIApplication.init
	
	def register_setting(self, setting_obj:T, on_save:Optional[Callable[[],None]]=None) -> T:
		'''
		Helper method to maintain a list of 'settings' objects
		that will be saved when save_settings is called.
		
		Pass on_save for anything you wish to do prior to a save event.
		
		Returns setting_obj for convenience.
		'''
		self._settings.append((setting_obj, on_save))
		return setting_obj
	
	def query_db(self, obj_type:Type[T], as_setting=False) -> T:
		'''
		Query the db for an object of type,
		construct it if it does not exist, and 
		registering it as a 'setting' to be saved as
		one when 'settings' are saved if as_setting is True.
		'''
		obj = AppContext.engine.query(obj_type).first()
		if obj is None:
			obj = obj_type()
		if as_setting:
			return self.register_setting(obj)
		return obj
	
	def save_settings(self, engine:Optional[StorageEngine]=None) -> None:
		'''
		Save all 'settings' registered with 'register_setting' to the
		passed storage engine, or to the one in app context if none
		is passed.
		'''
		if engine is None:
			engine = AppContext.engine
		
		for model in self.llmConfigs.models:
			model.new_id(True)
		
		for setting, on_save in self._settings:
			if on_save:
				on_save()
			engine.merge(setting)
	
	def export_settings(self, path:Optional[str]=None) -> dict:
		engine = JSONStorageEngine(DATA)
		self.save_settings(engine)
		settings = engine._data
		if path:
			directory = os.path.dirname(path)
			if len(directory)>0 and not os.path.exists(directory):
				os.makedirs(directory, exist_ok=True)
			with open(path, "w") as f:
				json.dump(settings, f, indent=4)
		return settings
	
	def import_settings(self, settings:Union[str, dict]) -> None:
		'''
		Imports the settings provided or at the path provided,
		into the main storage engine.
		'''
		if isinstance(settings, str):
			with open(settings, "r") as f:
				settings = json.load(f)
		
		def copy_into(new_obj, old_obj, closed_set:set=set()):
			ci = ClassInfo.get(type(new_obj))
			for field in ci.fields.values():
				if field.name == ci.primary_key_name:
					continue
				
				new_val = getattr(new_obj, field.name)
				if ClassInfo.get(field.type) is None:
					setattr(old_obj, field.name, new_val)
				else:
					old_val = getattr(old_obj, field.name)
					if old_val is None:
						setattr(old_obj, field.name, new_val)
					elif old_val not in closed_set:
						closed_set.add(old_val)
						copy_into(new_val, old_val, closed_set=closed_set)
		
		json_llm_settings :LLMConfigs = None
		engine = JSONStorageEngine(DATA, initial_data=settings)
		for setting_t in self._settings:
			setting = setting_t[0]
			setting_type = type(setting)
			
			json_setting = engine.query(setting_type).first()
			if setting_type is LLMConfigs:
				json_llm_settings = json_setting
				continue
			
			if json_setting is not None:
				copy_into(json_setting, setting)
			
		if json_llm_settings:
			exiting_models = {(type(model), model.user_model_name):model for model in self.llmConfigs.models}
			for model in json_llm_settings.models:
				model_key = (type(model), model.user_model_name)
				if model_key in exiting_models:
					old_model = exiting_models[model_key]
					copy_into(model, old_model)
				else:
					self.llmConfigs.models.append(model)
		
		self.save_settings()
		
	def _save_job(self, job:Job) -> None:
		'''Save's a single job. (triggered by Jobs.should_save_job after job completes)'''
		with AppContext.jobs._lock:
			AppContext.engine.merge(job)
	
	def save_jobs(self) -> None:
		'''Saves current jobs list to the db. (triggered by Jobs.changed event)'''
		with safe_stopwatch.timed_block("Save jobs"):
			with AppContext.jobs._lock:
				AppContext.engine.merge(AppContext.jobs)
	
	def transcription_work(self, job: TranscriptionJob) -> JobStatus:
		with safe_stopwatch.timed_block("Transcribe job work"):
			if job.audio:
				job.transcription = self.transcriber.transcribe(job.audio)
				return JobStatus.SUCCESS
			job.status_hover = "No audio supplied for transcription."
			return JobStatus.FAILED

	def transcription_callback(self, job: TranscriptionJob):
		self.transcription_completed(job.transcription)
	
	def text_to_speech_callback(self, job:TTSJob):
		#self.audio_player.play(job.data.speech)
		from pydub.playback import play
		play(job.data.speech)
		self.done_speaking = True
		
	def transcribe_live(self) -> Iterator[Transcription]:
		with TranscriptionIterator(self.audio_recorder, self.vad, stream_path="/home/charlie/_temp_stream_audio") as iterator:
			yield from iterator
			
	def __getitem__(self, model_name: str) -> LLM:
		if model_name not in self._llm_cache:
			for model_settings in self.llmConfigs.models:
				if model_settings.user_model_name == model_name:
					self._llm_cache[model_name] = model_settings
					break
			else:
				raise KeyError(f"No LLM model found with name: {model_name}")
		return self._llm_cache[model_name].model
	
	def llm_method(self, llm:LLM, key:str=None, with_history:bool=False, blocking:bool=True):
		from AbstractAI.LLMs.LLM_Helpers import llm_method
		return llm_method(
			llm=llm, key=key, 
			with_history=with_history, 
			blocking=blocking
		)
	
	def speak(self, text:str, blocking:bool=True):
		with safe_stopwatch.scope():
			with safe_stopwatch.timed_block("Speak"):
				if text is None or not isinstance(text, str) or len(text)==0:
					print(f"We were told to speak {text} in error.")
					return
				print(f"Speaking '{text}'")
				self.done_speaking = False
				# self.tts.speak(text)
				self.local_tts.speak(text)
				if blocking:
					while not getattr(self, 'done_speaking', False):
						time.sleep(0.01)
	
	def quit(self):
		'''Do all things needed to do before terminating the application.'''
		if getattr(self, 'has_quit', False):
			self.has_quit = True
			return
		
		AppContext.jobs.stop()
		self.save_jobs()
		self.save_settings()
	
	def sanitize_text(self, text:str) -> str:
		'''
		Makes text all lower case and removes all punctuation.
		'''
		# Tokenize the text
		tokens = word_tokenize(text.lower())
		
		# Remove punctuation and numbers
		tokens = [token for token in tokens if token.isalpha()]
		
		# Join the tokens back into a string
		processed_text = ' '.join(tokens)
		return processed_text.strip()
		
stopwatch.end_scope() #AbstractAI App Core Init
stopwatch("")
```
ApplicationCore.py

# Them, here is an example of the web UI
AbstractAI/web/static/styles.css
```css
.button {
    padding: 20px;
    margin: 10px;
    font-size: 18px;
    cursor: pointer;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 5px;
}

.terminal-view {
    height: calc(100vh - 200px);
    background: #000;
    color: #fff;
    padding: 10px;
    font-family: 'Courier New', monospace;
    position: relative;
    overflow: hidden;
}

#terminal-display {
    height: calc(100% - 30px);
    overflow-y: auto;
    white-space: pre;
    line-height: 1.2;
}

.terminal-line {
    height: 1.2em;
    position: relative;
}

.terminal-cursor {
    position: absolute;
    width: 0.6em;
    height: 1.2em;
    background: rgba(255, 255, 255, 0.7);
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
}

#terminal-container {
    outline: none; /* Remove focus outline */
    height: 100%;
    width: 100%;
}

.button:active {
    background-color: #3e8e41;
}

.button.clicked {
    animation: buttonClick 0.5s;
}

@keyframes buttonClick {
    0% { transform: scale(1); }
    50% { transform: scale(0.9); }
    100% { transform: scale(1); }
}

#transcription {
    padding: 10px;
    background-color: #f0f0f0;
    border-bottom: 1px solid #ddd;
}

.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
}

.content-area {
    flex: 1;
    padding: 20px;
    padding-bottom: 120px; /* Account for footer height */
    overflow-y: auto;
}

.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    z-index: 1000;
}

.menu-bar {
    background-color: #f8f8f8;
    padding: 10px;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
    border-top: 1px solid #ddd;
}

.conversation-list {
    margin: 20px;
    padding: 20px;
}

.conversation-item {
    padding: 15px;
    margin: 10px 0;
    border: 1px solid #ddd;
    border-radius: 5px;
    cursor: pointer;
    background-color: white;
    transition: all 0.2s ease;
}

.conversation-item:hover {
    background-color: #f0f0f0;
    transform: translateX(5px);
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
}

.conversation-description {
    font-size: 0.9em;
    color: #666;
    margin-top: 5px;
}

.no-conversations {
    padding: 20px;
    text-align: center;
    color: #666;
    font-style: italic;
    background-color: #f9f9f9;
    border-radius: 5px;
    margin: 20px 0;
}

.error-message {
    padding: 15px;
    margin: 10px 0;
    color: #721c24;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 5px;
    text-align: center;
}

.conversation-view {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
}

.message {
    display: flex;
    margin-bottom: 20px;
    gap: 20px;
    flex-direction: row;
}

.message-meta {
    flex: 0 0 200px;
    padding: 10px;
    border-radius: 5px;
}

.message-role {
    font-weight: bold;
    color: #333;
    margin-bottom: 5px;
}

.message-model-info {
    font-size: 0.9em;
    color: #666;
}

.model-name {
    margin-bottom: 5px;
}

.message-date {
    font-size: 0.8em;
}

.message-content {
    flex: 1;
    padding: 15px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    white-space: pre-wrap;
}

/* Role-specific colors */
.message-system .message-meta {
    background: #f5f5f5;
}

.message-assistant .message-meta {
    background: #ffe5e5;
}

.message-user .message-meta {
    background: #e5ffe5;
}

.no-messages {
    text-align: center;
    padding: 40px;
    color: #666;
    font-style: italic;
    background-color: #f9f9f9;
    border-radius: 5px;
    margin: 20px 0;
}

.message-input-container {
    padding: 20px;
    background: white;
    border-top: 1px solid #ddd;
    margin-top: 20px;
}

.message-input {
    display: block;
    width: 100%;
    min-height: 100px;
    height: 100px;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 5px;
    resize: vertical;
    font-family: inherit;
    font-size: 1em;
    box-sizing: border-box;
    margin: 0 auto;
    overflow: hidden; /* Prevent scrollbar from affecting layout */
}
```
styles.css
> I'd like that bit more broken up though, separate pieces for each screen and a core CSS like I mentioned before

AbstractAI/web/templates/base.html
```html
<!DOCTYPE html>
<html>
<head>
    <title>Voice Control Interface</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <div class="app-container">
        <h2 id="screen-title">{{ screen.title }}</h2>
        
        <div class="content-area">
            {% block content %}{% endblock %}
        </div>
        
        <div class="footer">
            {% include 'menu_bar.html' %}
            <div id="transcription">
                Last transcription: <span id="transcription-text"></span>
            </div>
        </div>
    </div>
    
    <div id="action-result"></div>

    <script>
        function triggerControl(controlId) {
            const button = document.getElementById(controlId);
            simulateButtonClick(button);
            
            const messageInput = document.getElementById('messageInput');
            if (messageInput && messageInput.value.trim() === '') {
                return; // Don't send empty messages
            }
            
            const formData = new FormData();
            if (messageInput) {
                formData.append('messageInput', messageInput.value);
            }
            formData.append('screen_id', '{{ screen.id }}');
            
            fetch(`/control/${controlId}`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.navigate) {
                    const messageInput = document.getElementById('messageInput');
                    if (messageInput) {
                        messageInput.value = ''; // Clear input before navigation
                    }
                    
                    // Force navigation or use loadScreen
                    if (data.force || data.navigate === window.location.pathname.substring(1)) {
                        window.location.href = '/' + data.navigate;
                        window.location.reload();
                    } else {
                        loadScreen(data.navigate);
                    }
                } else {
                    if (data.result) {
                        document.getElementById('action-result').textContent = data.result;
                    }
                }
            });
        }

        function loadScreen(screenId) {
            fetch(`/screen/${screenId}`)
                .then(response => {
                    if (!response.ok) {
                        // If screen not found, go back to conversations
                        window.location.href = '/conversations';
                        return;
                    }
                    return response.json();
                })
                .then(data => {
                    if (data) {
                        window.location.href = '/' + screenId;
                    }
                });
        }

        const eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(event) {
            if (!event.data) return;  // Skip keepalive messages
            
            const data = JSON.parse(event.data);
            if (data.text) {
                document.getElementById('transcription-text').textContent = data.text;
            }
            if (data.navigate) {
                window.location.href = '/' + data.navigate;
                // Force reload to ensure fresh state
                window.location.reload(true);
            } else if (data.action_result) {
                document.getElementById('action-result').textContent = data.action_result;
            }
        };

        // Reconnect if connection is lost
        eventSource.onerror = function(event) {
            console.log('EventSource failed, reconnecting...');
            eventSource.close();
            setTimeout(() => {
                eventSource = new EventSource('/stream');
            }, 1000);
        };

        function simulateButtonClick(button) {
            button.classList.add('clicked');
            setTimeout(() => {
                button.classList.remove('clicked');
            }, 500);
        }
    </script>
</body>
</html>
```
base.html

AbstractAI/web/templates/conversation_list.html
```html
{% extends "base.html" %}

{% block content %}
<div class="conversation-list">
    {% if error %}
        <div class="error-message">{{ error }}</div>
    {% endif %}
    
    {% if conversations %}
        {% for conv in conversations %}
        <div class="conversation-item" 
             title="{{ conv.description }}"
             onclick="openConversation('{{ conv.auto_id }}')">
            {{ loop.index }}. {{ conv.name }}
            {% if conv.description %}
            <div class="conversation-description">{{ conv.description }}</div>
            {% endif %}
        </div>
        {% endfor %}
    {% else %}
        <div class="no-conversations">
            No conversations found. Start a new one!
        </div>
    {% endif %}
</div>

<script>
function openConversation(convId) {
    if (convId) {
        fetch(`/conversation/${convId}`)
            .then(response => {
                if (response.ok) {
                    window.location.href = '/conversation/' + convId;
                } else {
                    console.error('Failed to load conversation:', convId);
                }
            });
    }
}
</script>
{% endblock %}
```
conversation_list.html

AbstractAI/web/templates/conversation.html
```html
{% extends "base.html" %}

{% block content %}
<div class="conversation-view">
    {% if messages %}
        {% for message in messages %}
        <div class="message message-{{ message.role.lower() }}">
            <div class="message-meta">
                <div class="message-role">{{ message.role }}</div>
                {% if message.is_model %}
                <div class="message-model-info">
                    {% if message.model_name %}
                    <div class="model-name">{{ message.model_name }}</div>
                    {% endif %}
                    {% if message.date %}
                    <div class="message-date">{{ message.date }}</div>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            <div class="message-content">{{ message.content }}</div>
        </div>
        {% endfor %}
    {% else %}
        <div class="no-messages">
            <p>No messages in this conversation yet.</p>
        </div>
    {% endif %}
    
    <div class="message-input-container">
        <form id="messageForm">
            <textarea id="messageInput" name="messageInput" class="message-input" placeholder="Type your message..."></textarea>
        </form>
    </div>
</div>

<script>
    function scrollToBottom() {
        window.scrollTo(0, document.body.scrollHeight);
    }
    
    // Scroll to bottom on page load
    window.onload = scrollToBottom;
</script>
{% endblock %}
```
conversation.html

AbstractAI/web/templates/index.html
```html
<!DOCTYPE html>
<html>
<head>
    <title>Voice Control Interface</title>
    <style>
        .button {
            padding: 20px;
            margin: 10px;
            font-size: 18px;
            cursor: pointer;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
        }
        .button:active {
            background-color: #3e8e41;
        }
        .button.clicked {
            animation: buttonClick 0.5s;
        }
        @keyframes buttonClick {
            0% { transform: scale(1); }
            50% { transform: scale(0.9); }
            100% { transform: scale(1); }
        }
        #transcription {
            margin-top: 20px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div id="screen">
        <h2 id="screen-title">{{ screen.title }}</h2>
        <div id="controls">
            {% for control in screen.controls %}
            <button class="button" 
                    id="{{ control.id }}" 
                    title="{{ ', '.join(control.keyphrases) if control.keyphrases else control.text }}"
                    onclick="triggerControl('{{ control.id }}')">
                {{ control.text }}
            </button>
            {% endfor %}
        </div>
    </div>
    
    <div id="action-result"></div>
    
    <div id="transcription">
        Last transcription: <span id="transcription-text"></span>
    </div>

    <script>
        function triggerControl(controlId) {
            const button = document.getElementById(controlId);
            simulateButtonClick(button);
            
            fetch(`/control/${controlId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    screen_id: '{{ screen.id }}'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.navigate) {
                    loadScreen(data.navigate);
                } else if (data.result) {
                    document.getElementById('action-result').textContent = data.result;
                }
            });
        }

        function loadScreen(screenId) {
            fetch(`/screen/${screenId}`)
                .then(response => response.json())
                .then(data => {
                    const screen = data.screen;
                    document.getElementById('screen-title').textContent = screen.title;
                    
                    const controls = document.getElementById('controls');
                    controls.innerHTML = '';
                    
                    screen.controls.forEach(control => {
                        const button = document.createElement('button');
                        button.className = 'button';
                        button.id = control.id;
                        button.textContent = control.text;
                        button.title = control.keyphrases ? control.keyphrases.join(', ') : control.text;
                        button.onclick = () => triggerControl(control.id);
                        controls.appendChild(button);
                    });
                });
        }

        const eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.text) {
                document.getElementById('transcription-text').textContent = data.text;
            }
            if (data.navigate) {
                loadScreen(data.navigate);
            } else if (data.action_result) {
                document.getElementById('action-result').textContent = data.action_result;
            }
        };

        function simulateButtonClick(button) {
            button.classList.add('clicked');
            setTimeout(() => {
                button.classList.remove('clicked');
            }, 500);
        }
    </script>
</body>
</html>
```
index.html

AbstractAI/web/templates/menu_bar.html
```html
<div class="menu-bar">
    {% for control in screen.controls %}
    <button class="button" 
            id="{{ control.id }}" 
            title="{{ ', '.join(control.keyphrases) if control.keyphrases else control.text }}"
            onclick="triggerControl('{{ control.id }}')">
        {{ control.text }}
    </button>
    {% endfor %}
</div>
```
menu_bar.html

AbstractAI/web/templates/terminal.html
```html
{% extends "base.html" %}

{% block content %}
<div class="terminal-view" id="terminal-container" tabindex="0">
    <div id="terminal-display"></div>
</div>

<script>
function renderTerminal(data) {
    const display = document.getElementById('terminal-display');
    display.innerHTML = '';
    
    const lines = data.raw_text.split('\n');
    const colors = data.color_json.colors;
    
    lines.forEach((line, y) => {
        const lineDiv = document.createElement('div');
        lineDiv.className = 'terminal-line';
        
        if (colors[y]) {
            colors[y].forEach((char, x) => {
                const span = document.createElement('span');
                span.textContent = char.char || ' ';
                
                let style = '';
                if (char.fg) style += `color: ${char.fg};`;
                if (char.bg) style += `background-color: ${char.bg};`;
                if (char.bold) style += 'font-weight: bold;';
                if (char.italics) style += 'font-style: italic;';
                if (char.underscore) style += 'text-decoration: underline;';
                if (char.strikethrough) style += 'text-decoration: line-through;';
                if (char.reverse) {
                    const temp = char.fg;
                    char.fg = char.bg;
                    char.bg = temp;
                }
                
                span.style = style;
                lineDiv.appendChild(span);
            });
        }
        
        display.appendChild(lineDiv);
    });
    
    // Position cursor
    const cursor = document.createElement('div');
    cursor.className = 'terminal-cursor';
    cursor.style.top = `${data.color_json.cursor.y * 1.2}em`;
    cursor.style.left = `${data.color_json.cursor.x * 0.6}em`;
    display.appendChild(cursor);
    
    // Scroll to bottom
    display.scrollTop = display.scrollHeight;
}

const terminal = document.getElementById('terminal-container');
terminal.focus();

terminal.addEventListener('keydown', function(e) {
    e.preventDefault(); // Prevent default browser actions
    
    let data = '';
    if (e.key === 'Enter') {
        data = '\n';
    } else if (e.key === 'Backspace') {
        data = '\b';
    } else if (e.key.length === 1) {
        data = e.key;
    } else if (e.key === 'Escape') {
        // Handle escape key for cancel
        fetch('/control/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'screen_id=terminal'
        })
        .then(response => response.json())
        .then(data => {
            if (data.navigate) {
                window.location.href = '/' + data.navigate;
            }
        });
        return;
    } else {
        return; // Ignore other special keys
    }
    
    fetch('/terminal/input', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ input: data })
    });
});

// Keep focus on terminal
terminal.addEventListener('blur', function() {
    terminal.focus();
});

// Poll for updates
let pollInterval;

function startPolling() {
    pollInterval = setInterval(() => {
        fetch('/terminal/screen')
            .then(response => response.json())
            .then(data => {
                renderTerminal(data);
            });
    }, 100);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Start polling when page loads
startPolling();

// Clean up when navigating away
window.addEventListener('beforeunload', stopPolling);

// Handle navigation events from the server
eventSource.onmessage = function(event) {
    if (!event.data) return;
    const data = JSON.parse(event.data);
    if (data.navigate) {
        stopPolling();
        window.location.href = '/' + data.navigate;
        window.location.reload(true);
        return;
    }
};

// Clean up when page is unloaded
window.addEventListener('unload', stopPolling);
</script>
{% endblock %}
```
terminal.html

AbstractAI/web/templates/welcome.html
```html
{% extends "base.html" %}

{% block content %}
<div class="welcome-screen">
    <div class="content-area">
        <!-- Welcome content can go here -->
    </div>
</div>
{% endblock %}
```
welcome.html