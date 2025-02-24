import uuid
from typing import Dict, Optional, Type, Union
from Alejandro.Models.control import Control
from Alejandro.Core.application import Application 
from Alejandro.Core.screen_stack import ScreenStack
from Alejandro.Core.string_word_stream import StringWordStream
from Alejandro.web.events import NavigationEvent, push_event
from Alejandro.Models.screen import Screen

class Session:
    """Manages application state for a browser session"""
    def __init__(self, welcome_screen: Screen):
        self.id = str(uuid.uuid4())
        self.screen_stack = ScreenStack(welcome_screen)
        self.last_active = datetime.now()
        
        # Create session-specific word stream and app
        self.word_stream = StringWordStream()
        self.core_app = Application(self.word_stream, welcome_screen)
        
    def navigate(self, target_screen: Union[Type[Screen], Screen]) -> None:
        """Navigate to a screen"""
        if isinstance(target_screen, type):
            screen = target_screen()
        else:
            screen = target_screen
            
        self.core_app.screen_stack.push(screen)
        push_event(NavigationEvent(
            screen_type=type(screen),
            session_id=self.id
        ))
        
    def go_back(self) -> None:
        """Pop current screen and return to previous"""
        if self.screen_stack.pop():
            current = self.screen_stack.current
            push_event(NavigationEvent(
                screen_type=type(current),
                session_id=self.id
            ))
            
    def go_forward(self) -> None:
        """Navigate forward in history if possible"""
        if self.screen_stack.forward():
            current = self.screen_stack.current
            push_event(NavigationEvent(
                screen_type=type(current),
                session_id=self.id
            ))
            
    def make_back_control(self) -> Control:
        """Create a back navigation control"""
        return Control(
            id="back",
            text="Back",
            keyphrases=["back", "go back", "return"],
            action=lambda s=self: s.go_back() if s else None
        )
        """Navigate forward in history if possible"""
        if self.screen_stack.forward():
            current = self.screen_stack.current
            push_event(NavigationEvent(
                screen_type=type(current),
                session_id=self.id
            ))

# Global session store
sessions: Dict[str, Session] = {}

from datetime import datetime, timedelta

def cleanup_sessions() -> None:
    """Remove inactive sessions older than 1 hour"""
    now = datetime.now()
    to_remove = []
    for session_id, session in sessions.items():
        if now - session.last_active > timedelta(hours=1):
            to_remove.append(session_id)
            
    for session_id in to_remove:
        from Alejandro.web.voice import stop_voice_control
        stop_voice_control(session_id)
        del sessions[session_id]

def get_or_create_session(session_id: Optional[str] = None, welcome_screen: Optional[Screen] = None) -> Session:
    """Get existing session or create new one"""
    cleanup_sessions()
    
    if session_id and session_id in sessions:
        sessions[session_id].last_active = datetime.now()
        return sessions[session_id]
        
    if not welcome_screen:
        from Alejandro.web.screens import WelcomeScreen
        welcome_screen = WelcomeScreen()
        
    session = Session(welcome_screen)
    sessions[session.id] = session
    
    # Start voice control for new session
    from Alejandro.web.voice import start_voice_control
    start_voice_control(session)
    
    return session
