from abc import ABC, abstractmethod
from typing import Iterator, List
from datetime import datetime
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab/english')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

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

    def process_text(self, text: str) -> List[WordNode]:
        """
        Convert a text string into a linked list of WordNodes.
        
        This is useful for testing and for processing text from other sources.
        The returned list contains WordNodes that are already linked together.
        """
        # Tokenize using NLTK
        tokens = nltk.word_tokenize(text.lower())
        
        # Keep alphanumeric tokens (words and numbers)
        tokens = [token for token in tokens if token.isalnum()]
        
        if not tokens:
            return []
            
        # Create nodes with timestamps
        nodes = []
        current_time = datetime.now()
        for token in tokens:
            start_time = current_time
            current_time = start_time.replace(microsecond=start_time.microsecond + 500000)
            node = WordNode(
                word=token,
                start_time=start_time,
                end_time=current_time
            )
            nodes.append(node)
            
        # Link nodes
        for i in range(len(nodes)-1):
            nodes[i].next = nodes[i+1]
            nodes[i+1].prev = nodes[i]
            
        return nodes
