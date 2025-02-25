from typing import Dict, Any
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.web.session import Session

class WelcomeScreen(Screen):
    """Initial welcome screen"""
    def __init__(self, session: ReferenceType['Session']):
        super().__init__(
            session=session,
            title="Welcome",
            controls=[
                Control(
                    id="activate",
                    text="Hey Alejandro",
                    keyphrases=["hey alejandro", "hello alejandro"],
                    action=lambda s=self: s.get_session().navigate(MainScreen)
                )
            ]
        )

class MainScreen(Screen):
    """Main menu screen"""
    def __init__(self, session: ReferenceType['Session']):
        super().__init__(
            session=session,
            title="Main Menu",
            controls=[
                Control(
                    id="conversations",
                    text="Conversations",
                    keyphrases=["conversations", "show conversations"],
                    action=lambda s=self: s.get_session().navigate(ConversationsScreen)
                ),
                Control(
                    id="terminal", 
                    text="Terminal",
                    keyphrases=["terminal", "open terminal"],
                    action=lambda s=self: s.get_session().navigate(TerminalScreen)
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=self: s.get_session().go_back()
                )
            ]
        )

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self, session: ReferenceType['Session']):
        super().__init__(
            session=session,
            title="Conversations",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=self: s.get_session().go_back()
            )]
        )
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "conversations": []  # TODO: Get actual conversations
        }

class TerminalScreen(Screen):
    """Terminal emulator screen"""
    def __init__(self, session: ReferenceType['Session']):
        super().__init__(
            session=session,
            title="Terminal",
            controls=[Control(
                id="back",
                text="Back",
                keyphrases=["back", "go back", "return"],
                action=lambda s=self: s.get_session().go_back()
            )]
        )
