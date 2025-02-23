from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class WordNode(BaseModel):
    """A node in a linked list of transcribed words"""
    word: str
    start_time: datetime
    end_time: datetime
    prev: Optional['WordNode'] = None 
    next: Optional['WordNode'] = None

    def __str__(self) -> str:
        return self.word
