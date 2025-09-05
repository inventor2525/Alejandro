from typing import List, Callable, Optional
from enum import Enum, auto
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.WordNode import WordNode
from RequiredAI.json_dataclass import *

class ModalState(Enum):
    """State of a modal control"""
    INACTIVE = auto()  # Not activated yet
    HOLDING = auto()   # Activated and collecting words

@json_dataclass
class ModalControl(Control):
    """A control that can enter a modal state to capture subsequent words"""
    
    deactivate_phrases: List[str]  # Phrases that exit modal state
    
    _state:ModalState = field(default=ModalState.INACTIVE, init=False, metadata=config(exclude=True))
    _collected_words:List[WordNode] = field(default_factory=list, init=False, metadata=config(exclude=True))
    
    @property
    def state(self) -> ModalState:
        """Get current state"""
        return self._state
        
    @property
    def collected_words(self) -> List[WordNode]:
        """Get words collected during modal state"""
        return self._collected_words
        
    def validate_word(self, word_node: WordNode) -> ControlResult:
        """Handle state transitions and word collection based on phrases"""
        if self._state == ModalState.HOLDING:
            self._collected_words.append(word_node)
            for phrase in self.deactivate_phrases:
                if self._check_phrase(phrase, word_node):
                    phrase_len = len(self._processed_phrases[phrase])
                    self._collected_words = self._collected_words[:-phrase_len]
                    self._state = ModalState.INACTIVE
                    if self.action:
                        self.action()
                    return ControlResult.USED
            return ControlResult.HOLD
        
        # Check activation phrases when inactive
        if self._check_phrase(self.text, word_node) or any(self._check_phrase(phrase, word_node) for phrase in self.keyphrases):
            self._state = ModalState.HOLDING
            self._collected_words = []
            return ControlResult.HOLD
        
        return ControlResult.UNUSED