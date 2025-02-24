from dataclasses import dataclass
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
    
    def to_json(self) -> Dict[str, Any]:
        """Convert event to JSON-serializable dict"""
        return {
            "type": self.__class__.__name__,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass 
class TranscriptionEvent(Event):
    """Event for new transcription text"""
    text: str = ""
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data["text"] = self.text
        return data

@dataclass
class NavigationEvent(Event):
    """Event for screen navigation"""
    screen_type: Type[Screen]
    force: bool = True
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "screen": self.screen_type.__name__.lower(),
            "force": self.force
        })
        return data

@dataclass
class ButtonClickEvent(Event):
    """Event for button/control activation"""
    control_id: str
    
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data["control_id"] = self.control_id
        return data

def push_event(event: Event) -> None:
    """Add event to queue"""
    event_queue.put(event)
