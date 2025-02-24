from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import queue

# Global event queue
event_queue = queue.Queue()

@dataclass
class Event:
    """Base event class"""
    timestamp: datetime = datetime.now()

@dataclass 
class TranscriptionEvent(Event):
    """Event for new transcription text"""
    text: str

@dataclass
class NavigationEvent(Event):
    """Event for screen navigation"""
    screen_name: str
    force: bool = True

@dataclass
class ButtonClickEvent(Event):
    """Event for button/control activation"""
    control_id: str

def push_event(event: Event) -> None:
    """Add event to queue"""
    event_queue.get_event(event)
