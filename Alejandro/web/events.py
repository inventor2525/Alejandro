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
        screen_name = self.screen_type.__name__.lower()
        if screen_name.endswith('screen'):
            #remove screen from the end of the name:
            screen_name = screen_name[:-len("screen")]
        data.update({
            "screen": screen_name,
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

def push_event(event: Event) -> None:
    """Add event to queue"""
    print(f"Pushing event: {event.__class__.__name__} for session {event.session_id}")
    print(f"Event data: {event.to_json()}")
    event_queue.put(event)
