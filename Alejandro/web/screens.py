from typing import Dict, Any
from Alejandro.Models.screen import Screen
from Alejandro.web.functions import make_back_control, make_nav_control

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
                    action=lambda s=None: navigate(s, MainScreen) if s else {}
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
                    action=lambda s=None: navigate(s, ConversationsScreen) if s else {}
                ),
                Control(
                    id="terminal", 
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda s=None: navigate(s, TerminalScreen) if s else {}
                ),
                make_back_control()
            ]
        )

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self):
        super().__init__(
            title="Conversations",
            controls=[make_back_control()]
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
            controls=[make_back_control()]
        )
