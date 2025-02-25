from typing import List, Optional
from Alejandro.Models.screen import Screen

class ScreenStack:
    """
    Manages navigation history for the application.
    Maintains the history of screens visited and handles screen lifecycle events.
    """
    def __init__(self, welcome_screen: Screen):
        self._stack: List[Screen] = [welcome_screen]
        self._forward_stack: List[Screen] = []
        
    def push(self, screen: Screen) -> None:
        """Push a new screen onto the stack"""
        self._stack.append(screen)
        self._forward_stack.clear()
        
    def pop(self) -> Optional[Screen]:
        """Pop current screen and return to previous"""
        if len(self._stack) > 1:
            popped = self._stack.pop()
            self._forward_stack.append(popped)
            return popped
        return None
        
    def forward(self) -> bool:
        """Navigate forward if possible"""
        if self._forward_stack:
            screen = self._forward_stack.pop()
            self._internal_push(screen)
            return True
        return False
        
    def _internal_push(self, screen: Screen) -> None:
        """Push without clearing forward stack"""
        self._stack.append(screen)
        
    @property
    def current(self) -> Screen:
        """Get current screen"""
        return self._stack[-1]
