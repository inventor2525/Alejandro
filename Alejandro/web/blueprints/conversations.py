from flask import Blueprint, render_template, request
from typing import Dict, Any, List
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.Models.modal_control import ModalControl

bp = Blueprint('conversations', __name__)

class ConversationsScreen(Screen):
    """List of conversations"""
    def __init__(self, session: 'Session'):
        super().__init__(
            session=session,
            title="Conversations",
            controls=[
                ModalControl(
                    id="select",
                    text="Select Conversation",
                    keyphrases=["select conversation", "choose conversation"],
                    deactivate_phrases=["end selection"],
                    action=lambda s=self: self._handle_selection()
                ),
                Control(
                    id="back",
                    text="Back", 
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=self: s.session().go_back()
                )
            ]
        )
        
    def _handle_selection(self) -> None:
        """Handle conversation selection from modal control"""
        # Get the selected text from modal control
        select_control = next(c for c in self.controls if c.id == "select")
        if not isinstance(select_control, ModalControl):
            return
            
        # Join collected words into selection text
        selection = " ".join(w.word for w in select_control.collected_words)
        
        # Find best matching conversation
        conversations = self.get_conversations()
        for conv in conversations:
            if selection.lower() in conv["name"].lower():
                # TODO: Navigate to conversation
                print(f"Selected conversation: {conv['name']}")
                break
    
    def get_conversations(self) -> List[Dict[str, str]]:
        """Get list of conversations"""
        # TODO: Get from database
        return [
            {"id": "1", "name": "First Chat", "description": "Initial conversation"},
            {"id": "2", "name": "Code Review", "description": "Reviewing pull request"},
            {"id": "3", "name": "Bug Report", "description": "Investigating crash"}
        ]
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "conversations": self.get_conversations()
        }

@bp.route('/conversationsscreen')
def conversations() -> str:
    """Conversations screen route"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
    
    session = get_or_create_session(session_id)
    screen = session.screen_stack.current
    
    return render_template(
        'base.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
