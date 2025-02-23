from abc import ABC, abstractmethod
from typing import Iterator, List
from Alejandro.Models.word_node import WordNode

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
