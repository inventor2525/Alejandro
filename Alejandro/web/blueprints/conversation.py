from flask import Blueprint, render_template, request
from typing import Dict, Any, List
from datetime import datetime
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type
from Alejandro.Core.Control import Control
from Alejandro.Core.ModelControl import ModalControl
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.web.events import ConversationUpdateEvent, push_event

bp = Blueprint('conversation', __name__)

@screen_type
class ConversationScreen(Screen):
    """Single conversation view"""
    conversation_id: str
    conversation: Conversation
    
    def __init__(self, session: 'Session', conversation_id: str):
        self.conversation_id = conversation_id
        try:
            self.conversation = Conversation.load(conversation_id)
        except FileNotFoundError:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        super().__init__(
            session=session,
            title=f"Conversation {self.conversation.short_id}",
            controls=[
                ModalControl(
                    id="speak",
                    text="Start Speaking",
                    keyphrases=["start speaking", "begin speaking"],
                    deactivate_phrases=["stop speaking", "end speaking"],
                    action=lambda s=self: s._handle_speech()
                ),
                Control(
                    id="send",
                    text="Send Message",
                    keyphrases=["send message"],
                    action=self._send_message,
                    js_getter_function="getMessageInput"
                ),
                session.make_back_control()
            ]
        )
        
        # Push initial conversation data
        self._push_update()
        
    def _handle_speech(self) -> None:
        """Handle speech input from modal control"""
        speak_control = next(c for c in self.controls if c.id == "speak")
        if not isinstance(speak_control, ModalControl):
            return
            
        text = " ".join(w.word for w in speak_control.collected_words)
        if text:
            # TODO: Append to message input
            print(f"Speech input: {text}")
            
    def _send_message(self, message_input:str) -> None:
        """Send current message"""
        if message_input:
            self.conversation.add_message(message_input)
            self.conversation.save()
            self._push_update()
        else:
            print("No message content provided")
        
    def _push_update(self):
        """Push conversation update event"""
        push_event(ConversationUpdateEvent(
            session_id=self.session.id,
            conversation_id=self.conversation_id,
            data=self.conversation.to_dict()
        ))

@bp.route(f'/{ConversationScreen.url()}')
def conversation() -> str:
    """Conversation screen route"""
    session_id = request.args.get('session')
    conversation_id = request.args.get('conversation_id')
    
    session = get_or_create_session(session_id)
    
    # Create conversation screen if needed
    screen = session.app.screen_stack.current
    if not isinstance(screen, ConversationScreen) or screen.conversation_id != conversation_id:
        screen = ConversationScreen(session, conversation_id)
        session.app.screen_stack.push(screen)
    
    return render_template(
        'conversation.html',
        screen=screen,
        session_id=session.id,
        conversation_id=conversation_id
    )
