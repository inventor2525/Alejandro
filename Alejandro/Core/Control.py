from typing import List, Callable, Optional, Dict, List, Any
from enum import Enum
from RequiredAI.json_dataclass import *
from Alejandro.Core.WordNode import WordNode
from Alejandro.Core.WordMapping import WORD_MAP
from Alejandro.Core.WordStream import WordStream

class ControlResult(Enum):
	"""Result of a control's validate_word() call"""
	UNUSED = 0      # Word was not used by this control
	USED = 1        # Word was used and consumed
	HOLD = 2        # Control is now modal and holding future words

@json_dataclass
class Control:
	"""A control that can be activated by voice commands"""
	id:str
	text: str  # Text shown on button/UI
	keyphrases: List[str]  # Alternative phrases that trigger this control
	action: Optional[callable]
	js_getter_function: Optional[str] = field(default=None, kw_only=True)
	js_return_handler: Optional[str] = field(default=None, kw_only=True)
	
	_phrase_words: Dict[str, List[str]] = field(default_factory=dict, init=False, metadata=config(exclude=True))
	
	def _check_phrase(self, phrase: str, streams_current_word: WordNode) -> bool:
		'''
		Checks if the passed phrase has JUST been spoken at this
		point in the word stream.
		
		In other words, is streams_current_word the last word
		in phrase?
		'''
		
		# Get the list of words that make up this phrase, 
		# and caching it if we didn't have it already:
		if phrase not in self._phrase_words:
			nodes = WordStream.process_text(phrase)
			self._phrase_words[phrase] = [n.word for n in nodes]
		words = self._phrase_words[phrase]
		
		# Walk backwards through phrase's words in lock step with
		# the word stream, starting at streams_current_word, looking to see
		# if this phrase matches.
		current = streams_current_word
		for target in reversed(words):
			if not current:
				return False
				
			target_word = target.lower()
			current_word = current.word.lower()
			
			# Get equivalent forms for current word if it's in the map
			if current_word in WORD_MAP:
				# Look to see that at least 1 matches the target word:
				if not any(target_word == form for form in WORD_MAP[current_word]):
					return False
			elif current_word != target_word:
				return False
				
			current = current.prev
		return True
	
	def validate_word(self, streams_current_word: WordNode) -> ControlResult:
		"""
		Check if this word completes any of our key phrases.
		Returns ControlResult indicating if/how the word was used.
		
		Unused meaning it didn't match, Used & Hold meaning it did
		but with Used then only this word will be used by this control
		whereas if hold is returned then this control will hold priority
		access to the word stream until it returns Used or Unused for a
		subsequent word.
		"""
		
		# Check if word completes the button text or any keyphrase
		if self._check_phrase(self.text, streams_current_word) or any(self._check_phrase(phrase, streams_current_word) for phrase in self.keyphrases):
			if self.action:
				self.action()
			return ControlResult.USED
			
		return ControlResult.UNUSED
