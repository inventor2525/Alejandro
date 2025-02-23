from abc import ABC, abstractmethod
from typing import Iterator, List, Optional
from datetime import datetime
from pydantic import BaseModel

class WordNode(BaseModel):
    """A node in a linked list of transcribed words"""
    word: str
    start_time: datetime
    end_time: datetime
    prev: Optional['WordNode'] = None 
    next: Optional['WordNode'] = None

    def __str__(self) -> str:
        return self.word

class WordStream(ABC):
    """
    Abstract interface for a stream of transcribed words.
    
    Implementations should handle the actual transcription process
    and word segmentation, while maintaining the linked list structure
    of WordNodes.
    """
    
    @abstractmethod
    def start_listening(self) -> None:
        """Start capturing and transcribing audio"""
        pass
        
    @abstractmethod
    def stop_listening(self) -> None:
        """Stop capturing and transcribing audio"""
        pass

    @abstractmethod
    def words(self) -> Iterator[WordNode]:
        """
        Iterate over transcribed words as they become available.
        
        This should continue yielding words even after stop_listening()
        is called, until all pending words are processed.
        """
        pass

    @abstractmethod
    def process_text(self, text: str) -> List[WordNode]:
        """
        Convert a text string into a linked list of WordNodes.
        
        This is useful for testing and for processing text from other sources.
        The returned list contains WordNodes that are already linked together.
        """
        pass
