from typing import List, Callable, Optional
from enum import Enum, auto
from Alejandro.Models.control import Control, ControlResult
from Alejandro.Models.word_node import WordNode

class ModalState(Enum):
    """State of a modal control"""
    INACTIVE = auto()  # Not activated yet
    HOLDING = auto()   # Activated and collecting words

class ModalControl(Control):
    """A control that can enter a modal state to capture subsequent words"""
    
    deactivate_phrases: List[str]  # Phrases that exit modal state
    
    def __init__(self, **data):
        super().__init__(**data)
        self._state = ModalState.INACTIVE
        self._collected_words: List[WordNode] = []
        
    @property
    def state(self) -> ModalState:
        """Get current state"""
        return self._state
        
    @property
    def collected_words(self) -> List[WordNode]:
        """Get words collected during modal state"""
        return self._collected_words
        
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """Check if word matches deactivation phrase when in modal state"""
        if self._state == ModalState.HOLDING:
            # Always collect the word first
            self._collected_words.append(word_node)
            
            # Then check for complete deactivation phrases
            for phrase in self.deactivate_phrases:
                if self._check_phrase(phrase, word_node):
                    # Remove the deactivation phrase words
                    phrase_len = len(self._processed_phrases[phrase])
                    self._collected_words = self._collected_words[:-phrase_len]
                    self._state = ModalState.INACTIVE
                    if self.action:
                        self.action()  # Call action on deactivation
                    return ControlResult.USED
            
            return ControlResult.HOLD
            
        # Check activation phrases when inactive
        if self._check_phrase(self.text, word_node) or any(self._check_phrase(phrase, word_node) for phrase in self.keyphrases):
            if self.action:
                self.action()
            self._state = ModalState.HOLDING
            self._collected_words = []
            return ControlResult.HOLD
            
        return ControlResult.UNUSED
