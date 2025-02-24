import uuid
from typing import Dict, Optional
from Alejandro.Core.application import Application 
from Alejandro.Core.screen_stack import ScreenStack
from Alejandro.Core.test_word_stream import TestWordStream
from Alejandro.Models.screen import Screen

class Session:
    """Manages application state for a browser session"""
    def __init__(self, welcome_screen: Screen):
        self.id = str(uuid.uuid4())
        self.screen_stack = ScreenStack(welcome_screen)
        
        # Create session-specific word stream and app
        self.word_stream = TestWordStream()
        self.core_app = Application(self.word_stream, welcome_screen)

# Global session store
sessions: Dict[str, Session] = {}

def get_or_create_session(session_id: Optional[str] = None, welcome_screen: Optional[Screen] = None) -> Session:
    """Get existing session or create new one"""
    if session_id and session_id in sessions:
        return sessions[session_id]
        
    if not welcome_screen:
        from Alejandro.web.screens import WelcomeScreen
        welcome_screen = WelcomeScreen()
        
    session = Session(welcome_screen)
    sessions[session.id] = session
    return session
