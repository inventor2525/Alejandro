from typing import Dict, Any
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.web.functions import navigate, go_back

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
                    action=lambda: navigate(MainScreen)
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
                    action=lambda: navigate(ConversationsScreen)
                ),
                Control(
                    id="terminal",
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda: navigate(TerminalScreen)
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back"],
                    action=go_back
                )
            ]
        )

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
                    action=go_back
                )
            ]
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
            controls=[
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back"],
                    action=go_back
                )
            ]
        )
