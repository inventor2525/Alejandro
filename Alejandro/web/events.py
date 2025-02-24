from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
