from flask import Blueprint, render_template, request
from typing import Dict, Any, List
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen
from Alejandro.Core.Control import Control
from Alejandro.Core.ModelControl import ModalControl

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
                session.make_back_control()
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

@bp.route(f'/{ConversationsScreen.url()}')
def conversations() -> str:
    """Conversations screen route"""
    session_id = request.args.get('session')
    if not session_id:
        return "No session ID provided", 400
    
    session = get_or_create_session(session_id)
    screen = session.app.screen_stack.current
    
    template_data = screen.get_template_data()
    print(f"Rendering conversations with data: {template_data}")
    
    return render_template(
        'conversation_list.html',
        screen=screen,
        session_id=session.id,
        **template_data
    )
