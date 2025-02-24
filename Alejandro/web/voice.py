import threading
from typing import Optional
from Alejandro.Core.application import Application
from Alejandro.Core.test_word_stream import TestWordStream
from Alejandro.Models.screen import Screen
from Alejandro.web.events import Event

# Global app instance
core_app: Optional[Application] = None
word_stream: Optional[TestWordStream] = None

def init_app(welcome_screen: Screen) -> None:
    """Initialize the core application"""
    global core_app, word_stream
    if core_app is None:
        word_stream = TestWordStream()
        core_app = Application(word_stream, welcome_screen)

def voice_control_thread() -> None:
    """Background thread for voice processing"""
    try:
        core_app.run()
    except Exception as e:
        print(f"Voice control error: {e}")

def start_voice_control() -> None:
    """Start voice control in background thread"""
    thread = threading.Thread(target=voice_control_thread)
    thread.daemon = True
    thread.start()
