import uuid
from typing import Dict, Optional, Type, Union, TypeVar
from weakref import ref, ReferenceType
from Alejandro.Models.control import Control
from Alejandro.Core.application import Application 
from Alejandro.Core.screen_stack import ScreenStack
from Alejandro.Core.string_word_stream import StringWordStream
from Alejandro.web.events import NavigationEvent, push_event
from Alejandro.Models.screen import Screen
from Alejandro.web.terminal import Terminal

class Session:
    """Manages application state for a browser session"""
    def __init__(self, welcome_screen_type: Type[Screen]):
        self.id = str(uuid.uuid4())
        self.last_active = datetime.now()
        self._screens: Dict[Type[Screen], Screen] = {}
        self.terminals: Dict[str, 'Terminal'] = {}
        self.current_terminal_index = 0
        
        # Create session-specific word stream and app
        self.word_stream = StringWordStream()
        welcome_screen = self.get_screen(welcome_screen_type)
        self.screen_stack = ScreenStack(welcome_screen)
        self.core_app = Application(self.word_stream, welcome_screen)
        
        # Share screen stack between app and session
        self.core_app.screen_stack = self.screen_stack
        
    def get_screen(self, screen_type: Type[Screen]) -> Screen:
        """Get existing screen instance or create new one"""
        if screen_type not in self._screens:
            screen = screen_type(session=self)
            self._screens[screen_type] = screen
        return self._screens[screen_type]
        
    def navigate(self, target_screen: Union[Type[Screen], Screen]) -> None:
        """Navigate to a screen"""
        if isinstance(target_screen, type):
            screen = self.get_screen(target_screen)
        else:
            screen = target_screen
            
        self.core_app.screen_stack.push(screen)
        print(f"Pushing navigation event for screen: {type(screen).__name__} with session: {self.id}")
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
        
        # Close all terminals
        for terminal in sessions[session_id].terminals.values():
            terminal.close()
            
        del sessions[session_id]

def get_or_create_session(session_id: Optional[str] = None) -> Session:
    """Get existing session or create new one"""
    cleanup_sessions()
    
    if session_id and session_id in sessions:
        print(f"Reusing existing session: {session_id}")
        sessions[session_id].last_active = datetime.now()
        return sessions[session_id]
        
    from Alejandro.web.blueprints.welcome import WelcomeScreen
    if session_id:
        print(f"Creating new session with provided ID: {session_id}")
        session = Session(WelcomeScreen)
        session.id = session_id  # Use provided ID instead of generating new one
    else:
        print("Creating new session with generated ID")
        session = Session(WelcomeScreen)
        
    sessions[session.id] = session
    
    # Start voice control for new session
    from Alejandro.web.voice import start_voice_control
    start_voice_control(session)
    
    return session
