from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Type, Dict, Any
import queue
from Alejandro.Models.screen import Screen

# Global event queue
event_queue = queue.Queue()

@dataclass
class Event:
    """Base event class"""
    timestamp: datetime = datetime.now()
    session_id: str = field(kw_only=True)
    
    def to_json(self) -> Dict[str, Any]:
        """Convert event to JSON-serializable dict"""
        return {
            "type": self.__class__.__name__,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id
        }

@dataclass
class TranscriptionEvent(Event):
    """Event for new transcription text"""
    text: str = field(kw_only=True)
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data["text"] = self.text
        return data

@dataclass
class NavigationEvent(Event):
    """Event for screen navigation"""
    screen_type: Type[Screen] = field(kw_only=True)
    force: bool = True
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "screen": self.screen_type.url(),
            "force": self.force
        })
        return data

@dataclass
class ButtonClickEvent(Event):
    """Event for button/control activation"""
    control_id: str = field(kw_only=True)
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data["control_id"] = self.control_id
        return data

@dataclass
class TerminalScreenEvent(Event):
    """Event for terminal screen updates"""
    terminal_id: str = field(kw_only=True)
    raw_text: str = field(kw_only=True)
    color_json: Dict[str, Any] = field(kw_only=True)
    cursor_position: Dict[str, int] = field(kw_only=True)
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "terminal_id": self.terminal_id,
            "raw_text": self.raw_text,
            "color_json": self.color_json,
            "cursor_position": self.cursor_position
        })
        return data

def push_event(event: Event) -> None:
    """Add event to queue"""
    # Don't log the full event data for terminal events
    if isinstance(event, TerminalScreenEvent):
        print(f"Pushing terminal event for session {event.session_id}, terminal {event.terminal_id}")
    else:
        print(f"Pushing event: {event.__class__.__name__} for session {event.session_id}")
        print(f"Event data: {event.to_json()}")
    
    event_queue.put(event)
