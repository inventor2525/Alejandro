from datetime import datetime
from typing import Optional
from RequiredAI.json_dataclass import json_dataclass

@json_dataclass
class WordNode:
    """A node in a linked list of transcribed words"""
    word: str
    start_time: datetime
    end_time: datetime
    prev: Optional['WordNode'] = None 
    next: Optional['WordNode'] = None

    def __str__(self) -> str:
        return self.word
