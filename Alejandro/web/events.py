from RequiredAI.json_dataclass import json_dataclass, config, field
from typing import Optional, Type, Dict, Any
from datetime import datetime
import queue
from Alejandro.Core.Screen import Screen

# Global event queue
event_queue = queue.Queue()

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
