import threading
from typing import Dict
from Alejandro.web.session import Session
from Alejandro.web.events import Event

# Track voice control threads by session
voice_threads: Dict[str, threading.Thread] = {}

def voice_control_thread(session: Session) -> None:
    """Background thread for voice processing"""
    try:
        session.core_app.run()
    except Exception as e:
        print(f"Voice control error for session {session.id}: {e}")

def start_voice_control(session: Session) -> None:
    """Start voice control in background thread for session"""
    if session.id not in voice_threads:
        thread = threading.Thread(target=voice_control_thread, args=(session,))
        thread.daemon = True
        thread.start()
        voice_threads[session.id] = thread

def stop_voice_control(session_id: str) -> None:
    """Stop voice control for session"""
    if session_id in voice_threads:
        # Thread will terminate when session is cleaned up
        del voice_threads[session_id]
