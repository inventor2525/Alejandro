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
	def collected_words(self) -> str:
		"""
		The words collected between any start and end phrase used,
		the last time they were used.
		
		Note that this is only intended to be called at the moment the end
		phrase has just been spoken. If you call this property before the
		end phrase is spoken fully it may contain the first few words of
		the end phrase.
		"""
		return " ".join([w.word for w in self._collected_words])
		
	def validate_word(self, word_node: WordNode) -> ControlResult:
		"""Handle state transitions and word collection based on phrases"""
		if self._state == ModalState.HOLDING:
			# append any words since we started holding control of the word stream:
			self._collected_words.append(word_node)
			
			for phrase in self.deactivate_phrases:
				if self._check_phrase(phrase, word_node):
					# Stop holding the word stream
					self._state = ModalState.INACTIVE
					
					# Collect just the words that are not part of the end phrase (or start phrase):
					phrase_len = len(self._phrase_words[phrase])
					self._collected_words = self._collected_words[:-phrase_len]
					return ControlResult.USED
			return ControlResult.HOLD
		
		# Check activation phrases when inactive
		if self._check_phrase(self.text, word_node) or any(self._check_phrase(phrase, word_node) for phrase in self.keyphrases):
			self._state = ModalState.HOLDING
			self._collected_words = []
			return ControlResult.HOLD
		
		return ControlResult.UNUSED