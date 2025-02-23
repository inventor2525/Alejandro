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
    
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """
        Check if this word completes any of our key phrases by looking backwards.
        Returns ControlResult indicating if/how the word was used.
        """
        def check_phrase(phrase: str) -> bool:
            words = phrase.lower().split()
            current = word_node
            
            # Walk backwards through phrase words
            for target in reversed(words):
                if not current or current.word.lower() != target:
                    return False
                current = current.prev
            return True
            
        # Check if word completes the button text or any keyphrase
        if check_phrase(self.text) or any(check_phrase(phrase) for phrase in self.keyphrases):
            if self.action:
                self.action()
            return ControlResult.USED
            
        return ControlResult.UNUSED
