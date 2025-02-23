from typing import List, Callable, Optional
from enum import Enum
from pydantic import BaseModel
from Alejandro.Models.word_node import WordNode

class ControlResult(Enum):
    """Result of a control's validate_word() call"""
    UNUSED = 0      # Word was not used by this control
    USED = 1        # Word was used and consumed
    HOLD = 2        # Control is now modal and holding future words

class Control(BaseModel):
    """A control that can be activated by voice commands"""
    
    text: str  # Text shown on button/UI
    keyphrases: List[str]  # Alternative phrases that trigger this control
    action: Optional[Callable[[], None]] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Cache processed word lists
        self._processed_phrases = {}
        
    def _check_phrase(self, phrase: str, word_node: WordNode) -> bool:
        """Check if word_node completes the given phrase by looking backwards"""
        # Get or create processed word list
        if phrase not in self._processed_phrases:
            from Alejandro.Interfaces.word_stream import WordStream
            nodes = WordStream.process_text(phrase)
            self._processed_phrases[phrase] = [n.word for n in nodes]
            
        words = self._processed_phrases[phrase]
        current = word_node
        
        # Walk backwards through phrase words
        for target in reversed(words):
            if not current or current.word.lower() != target:
                return False
            current = current.prev
        return True
        
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """
        Check if this word completes any of our key phrases by looking backwards.
        Returns ControlResult indicating if/how the word was used.
        """
        # Check if word completes the button text or any keyphrase
        if self._check_phrase(self.text, word_node) or any(self._check_phrase(phrase, word_node) for phrase in self.keyphrases):
            if self.action:
                self.action()
            return ControlResult.USED
            
        return ControlResult.UNUSED
