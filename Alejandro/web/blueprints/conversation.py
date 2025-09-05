from flask import Blueprint, render_template, request
from typing import Dict, Any, List, Optional
from datetime import datetime
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen
from Alejandro.Core.Control import Control
from Alejandro.Core.ModelControl import ModalControl

bp = Blueprint('conversation', __name__)

class ConversationScreen(Screen):
    """Single conversation view"""
    conversation_id: str
    
    def __init__(self, session: 'Session', conversation_id: str):
        super().__init__(
            session=session,
            title=f"Conversation {conversation_id}",
            controls=[
                ModalControl(
                    id="speak",
                    text="Start Speaking",
                    keyphrases=["start speaking", "begin speaking"],
                    deactivate_phrases=["stop speaking", "end speaking"],
                    action=lambda s=self: self._handle_speech()
                ),
                Control(
                    id="send",
                    text="Send Message",
                    keyphrases=["send message", "send", "submit"],
                    action=lambda s=self: self._send_message()
                ),
                Control(
                    id="back",
                    text="Back",
                    keyphrases=["back", "go back", "return"],
                    action=lambda s=self: s.session().go_back()
                )
            ],
            conversation_id = conversation_id
        )
        
    def _handle_speech(self) -> None:
        """Handle speech input from modal control"""
        speak_control = next(c for c in self.controls if c.id == "speak")
        if not isinstance(speak_control, ModalControl):
            return
            
        text = " ".join(w.word for w in speak_control.collected_words)
        if text:
            # TODO: Append to message input
            print(f"Speech input: {text}")
            
    def _send_message(self) -> None:
        """Send current message"""
        # TODO: Actually send message
        print("Sending message")
        
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        # TODO: Get from database
        return [
            {
                "role": "User",
                "content": "Can you help me with a Python problem?",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_model": False
            },
            {
                "role": "Assistant",
                "content": "Of course! What's the issue you're having?",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_model": True,
                "model_name": "GPT-4"
            }
        ]
        
    def get_template_data(self) -> Dict[str, Any]:
        return {
            "messages": self.get_messages()
        }

@bp.route(f'/{ConversationScreen.url()}')
def conversation() -> str:
    """Conversation screen route"""
    session_id = request.args.get('session')
    conversation_id = request.args.get('conversation_id')
    
    if not session_id or not conversation_id:
        return "Missing session_id or conversation_id", 400
        
    session = get_or_create_session(session_id)
    
    # Create conversation screen if needed
    screen = session.screen_stack.current
    if not isinstance(screen, ConversationScreen) or screen.conversation_id != conversation_id:
        screen = ConversationScreen(session, conversation_id)
        session.screen_stack.push(screen)
    
    return render_template(
        'conversation.html',
        screen=screen,
        session_id=session.id,
        **screen.get_template_data()
    )
