from typing import Dict, Any
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.web.session import Session

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
                    action=lambda s=None: s.navigate(MainScreen) if s else None
                )
            ]
        )

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
                    action=lambda s=None: s.navigate(ConversationsScreen) if s else None
                ),
                Control(
                    id="terminal", 
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda s=None: s.navigate(TerminalScreen) if s else None
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=None: s.go_back() if s else None
                )
            ]
        )

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self):
        super().__init__(
            title="Conversations",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=None: s.go_back() if s else None
            )]
        )
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "conversations": []  # TODO: Get actual conversations
        }

class TerminalScreen(Screen):
    """Terminal emulator screen"""
    def __init__(self):
        super().__init__(
            title="Terminal",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=None: s.go_back() if s else None
            )]
        )
