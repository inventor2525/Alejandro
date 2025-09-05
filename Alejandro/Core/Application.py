from typing import List, Optional, Callable
from Alejandro.Core.WordStream import WordStream
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.Screen import Screen
from Alejandro.Core.ScreenStack import ScreenStack

class Application:
    """
    Core application class that processes words from a WordStream
    and manages screens/controls.
    """
    def __init__(self, word_stream: WordStream, welcome_screen: Screen):
        self.word_stream = word_stream
        self.screen_stack = ScreenStack(welcome_screen)
        self.global_word_handlers: List[Callable[[str], None]] = []
        self._modal_control: Optional[Control] = None
        
    def run(self) -> None:
        """Start processing words from the stream"""
        self.word_stream.start_listening()
        
        try:
            for word in self.word_stream.words():
                # Notify global handlers
                for handler in self.global_word_handlers:
                    handler(word.word)
                    
                # Process through current screen's controls
                if self._modal_control:
                    result = self._modal_control.validate_word(word)
                    if result == ControlResult.USED:
                        self._modal_control = None
                else:
                    for control in self.screen_stack.current.controls:
                        result = control.validate_word(word)
                        if result == ControlResult.USED:
                            break
                        elif result == ControlResult.HOLD:
                            self._modal_control = control
                            if control.action:
                                control.action()
                            break
                            
        finally:
            self.word_stream.stop_listening()
            
    def add_global_word_handler(self, handler: Callable[[str], None]) -> None:
        """Add a handler that receives all words regardless of controls"""
        self.global_word_handlers.append(handler)
