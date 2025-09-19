from RequiredAI.json_dataclass import json_dataclass, config, field
from typing import Optional, Type, Dict, Any, Iterator
from datetime import datetime
import queue
from Alejandro.Core.Screen import Screen
from flask import Blueprint, Response, request
import time

# Global event queue
event_queue = queue.Queue()
events_bp = Blueprint('events', __name__)

@json_dataclass
class Event:
    """Base event class"""
    type:str = field(default=None, init=False)
    timestamp: datetime = field(
        default_factory=lambda:datetime.now(), init=False,
        metadata=config(encoder=lambda d:d.isoformat(),
                        decoder=lambda iso_d:datetime.fromisoformat(iso_d)
    ))
    session_id: str = field(kw_only=True)
    
    def __post_init__(self):
        self.type = self.__class__.__name__

@json_dataclass
class TranscriptionEvent(Event):
    """Event for new transcription text"""
    text: str = field(kw_only=True)

@json_dataclass
class NavigationEvent(Event):
    """Event for screen navigation"""
    screen: Type[Screen] = field(kw_only=True, metadata=config(
        encoder=lambda s:s.url()
    ))

@json_dataclass
class ButtonClickEvent(Event):
    """Event for button/control activation"""
    control_id: str = field(kw_only=True)

@json_dataclass
class TerminalScreenEvent(Event):
    """Event for terminal screen updates"""
    terminal_id: str = field(kw_only=True)
    raw_text: str = field(kw_only=True)

def push_event(event: Event) -> None:
    """Add event to queue"""
    if isinstance(event, TerminalScreenEvent):
        print(f"Pushing terminal event for session {event.session_id}, terminal {event.terminal_id}")
    else:
        print(f"Pushing event: {event.__class__.__name__} ({event.to_json()}) for session {event.session_id}")
    
    event_queue.put(event)

@events_bp.route('/event_stream')
def event_stream() -> Response:
    """SSE endpoint"""
    session_id = request.args.get('session')
    
    if not session_id:
        return Response("No session ID provided", status=400)
    
    #Ensure the session exists:
    from Alejandro.web.session import get_or_create_session
    get_or_create_session(session_id)
    
    def event_stream(session_id: str) -> Iterator[str]:
        while True:
            try:
                event = event_queue.get_nowait()
                if isinstance(event, Event):
                    if event.session_id == session_id:
                        yield f"data: {event.to_json()}\n\n"
            except queue.Empty:
                pass
            
            # Keep-alive
            time.sleep(0.01)
            yield ": keepalive\n\n"
            
    return Response(
        event_stream(session_id),
        mimetype='text/event-stream'
    )