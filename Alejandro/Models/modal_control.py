from typing import List, Callable, Optional
from Alejandro.Models.control import Control, ControlResult
from Alejandro.Models.word_node import WordNode

class ModalControl(Control):
    """A control that can enter a modal state to capture subsequent words"""
    
    deactivate_phrases: List[str]  # Phrases that exit modal state
    
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """Check if word matches deactivation phrase when in modal state"""
        # When activated, check for deactivation phrases
        if any(self._check_phrase(phrase, word_node) for phrase in self.deactivate_phrases):
            return ControlResult.USED
            
        # Check normal activation phrases
        if self._check_phrase(self.text, word_node) or any(self._check_phrase(phrase, word_node) for phrase in self.keyphrases):
            if self.action:
                self.action()
            return ControlResult.HOLD
            
        return ControlResult.UNUSED
