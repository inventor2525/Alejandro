from datetime import datetime
from typing import Iterator
import sys
from Alejandro.Interfaces.word_stream import WordStream
from Alejandro.Models.word_node import WordNode

class TestWordStream(WordStream):
    """A WordStream that reads input from terminal for testing"""
    
    def __init__(self):
        self.is_listening = False
        
    def start_listening(self) -> None:
        self.is_listening = True
        
    def stop_listening(self) -> None:
        self.is_listening = False
        
    def words(self) -> Iterator[WordNode]:
        """Yield words from terminal input"""
        print("\nEnter text (Ctrl+C to exit):")
        try:
            while True:
                text = input("> ")
                if text.strip():
                    # Process text into word nodes
                    nodes = self.process_text(text)
                    for node in nodes:
                        yield node
        except KeyboardInterrupt:
            print("\nStopping word stream")
