from typing import Dict, Any, List
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control

class WelcomeScreen(Screen):
    """Initial welcome screen"""
    def __init__(self):
        super().__init__(
            title="Welcome",
            controls=[
                Control(
                    id="activate",
                    text="Hey Alejandro",
                    keyphrases=["hey alejandro", "hello alejandro"],
                    action=lambda: self._goto_main()
                )
            ]
        )
    
    def _goto_main(self) -> Dict[str, Any]:
        """Navigate to main screen"""
        from Alejandro.web.app import core_app
        core_app.screen_stack.push(MainScreen())
        return {"navigate": "main"}

class MainScreen(Screen):
    """Main menu screen"""
    def __init__(self):
        super().__init__(
            title="Main Menu",
            controls=[
                Control(
                    id="conversations",
                    text="Conversations",
                    keyphrases=["conversations", "show conversations"],
                    action=lambda: self._goto_conversations()
                ),
                Control(
                    id="terminal",
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda: self._goto_terminal()
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back"],
                    action=lambda: self._go_back()
                )
            ]
        )
    
    def _goto_conversations(self) -> Dict[str, Any]:
        from Alejandro.web.app import core_app
        core_app.screen_stack.push(ConversationsScreen())
        return {"navigate": "conversations"}
        
    def _goto_terminal(self) -> Dict[str, Any]:
        from Alejandro.web.app import core_app
        core_app.screen_stack.push(TerminalScreen())
        return {"navigate": "terminal"}
        
    def _go_back(self) -> Dict[str, Any]:
        from Alejandro.web.app import core_app
        if core_app.screen_stack.pop():
            return {"navigate": "welcome"}
        return {}

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self):
        super().__init__(
            title="Conversations",
            controls=[
                Control(
                    id="back",
                    text="Back", 
                    keyphrases=["back", "go back"],
                    action=lambda: self._go_back()
                )
            ]
        )
    
    def _go_back(self) -> Dict[str, Any]:
        from Alejandro.web.app import core_app
        if core_app.screen_stack.pop():
            return {"navigate": "main"}
        return {}
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "conversations": []  # TODO: Get actual conversations
        }

class TerminalScreen(Screen):
    """Terminal emulator screen"""
    def __init__(self):
        super().__init__(
            title="Terminal",
            controls=[
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back"], 
                    action=lambda: self._go_back()
                )
            ]
        )
    
    def _go_back(self) -> Dict[str, Any]:
        from Alejandro.web.app import core_app
        if core_app.screen_stack.pop():
            return {"navigate": "main"}
        return {}
