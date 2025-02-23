from typing import List, Callable, Optional
from Alejandro.Models.control import Control, ControlResult
from Alejandro.Models.word_node import WordNode

class ModalControl(Control):
    """A control that can enter a modal state to capture subsequent words"""
    
    deactivate_phrases: List[str]  # Phrases that exit modal state
    
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """Check if word matches deactivation phrase when in modal state"""
        def check_phrase(phrase: str) -> bool:
            words = phrase.lower().split()
            current = word_node
            
            # Walk backwards through phrase words
            for target in reversed(words):
                if not current or current.word.lower() != target:
                    return False
                current = current.prev
            return True
            
        # When activated, check for deactivation phrases
        if any(check_phrase(phrase) for phrase in self.deactivate_phrases):
            return ControlResult.USED
            
        # Check normal activation phrases
        if check_phrase(self.text) or any(check_phrase(phrase) for phrase in self.keyphrases):
            if self.action:
                self.action()
            return ControlResult.HOLD
            
        return ControlResult.UNUSED
