from datetime import datetime, timedelta
from typing import Iterator, List
from Alejandro.Interfaces.word_stream import WordStream
from Alejandro.Models.word_node import WordNode

class StringWordStream(WordStream):
    """A WordStream implementation that processes strings for testing"""
    
    def __init__(self):
        self.words_to_stream: List[str] = []
        self.is_listening = False
        self.current_time = datetime.now()
        
    def start_listening(self) -> None:
        self.is_listening = True
        
    def stop_listening(self) -> None:
        self.is_listening = False
        
    def add_words(self, text: str) -> None:
        """Add words to be streamed"""
        self.words_to_stream.extend(text.split())
        
    def words(self) -> Iterator[WordNode]:
        """Yield words that were added via add_words()"""
        for word in self.words_to_stream:
            start_time = self.current_time
            self.current_time += timedelta(milliseconds=500)
            node = WordNode(
                word=word.lower(),
                start_time=start_time,
                end_time=self.current_time
            )
            yield node
