from typing import Dict, Any
from Alejandro.Models.screen import Screen
from Alejandro.web.functions import make_back_control, make_nav_control

class WelcomeScreen(Screen):
    """Initial welcome screen"""
    def __init__(self):
        super().__init__(
            title="Welcome",
            controls=[
                make_nav_control(
                    id="activate",
                    text="Hey Alejandro",
                    target_screen=MainScreen,
                    keyphrases=["hey alejandro", "hello alejandro"]
                )
            ]
        )

class MainScreen(Screen):
    """Main menu screen"""
    def __init__(self):
        super().__init__(
            title="Main Menu",
            controls=[
                make_nav_control(
                    id="conversations",
                    text="Conversations", 
                    target_screen=ConversationsScreen,
                    keyphrases=["conversations", "show conversations"]
                ),
                make_nav_control(
                    id="terminal",
                    text="Terminal",
                    target_screen=TerminalScreen,
                    keyphrases=["terminal", "open terminal"]
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
