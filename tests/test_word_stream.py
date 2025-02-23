from datetime import datetime, timedelta
from typing import Iterator, List
from Alejandro.Models.word_node import WordNode
from Alejandro.Interfaces.word_stream import WordStream

class TestWordStream(WordStream):
    """A simple WordStream implementation for testing"""
    
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
            

def test_word_stream():
    """Test the TestWordStream implementation"""
    stream = TestWordStream()
    
    # Test process_text
    nodes = stream.process_text("Hello World")
    assert len(nodes) == 2
    assert nodes[0].word == "hello"
    assert nodes[0].next == nodes[1]
    assert nodes[1].prev == nodes[0]
    assert nodes[1].word == "world"
    
    # Test streaming
    stream.start_listening()
    stream.add_words("Testing the stream")
    
    words = []
    for word in stream.words():
        words.append(word.word)
    
    assert words == ["testing", "the", "stream"]
    
    stream.stop_listening()
