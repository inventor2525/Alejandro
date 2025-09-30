from typing import List, Optional, Callable, Dict
from enum import Enum, auto
from Alejandro.Core.Signal import Signal
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.WordNode import WordNode
from RequiredAI.client import RequiredAIClient
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.Requirement import Requirements
from RequiredAI.ModelConfig import ModelConfig
from Alejandro.Models.Conversation import Conversation, Message, Roles
from threading import Thread

class Assistant:
    """Manages AI conversations for a session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.screen_should_update = Signal[[str, Conversation], None]()
        self.current_conversation: Optional[Conversation] = None
        self.client = RequiredAIClient(base_url="http://localhost:5432")  # Adjust URL as needed
        self.current_model = "SimpleAI"
        
        llama_model_config = ModelConfig(
            name="llama",
            provider="groq",
            provider_model="llama-3.3-70b-versatile",#"llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY"
        )
        
        simple_ai_config = ModelConfig(
            name=self.current_model,
            provider="RequiredAI",
            provider_model="llama",
            requirements=[
                WrittenRequirement(
                    evaluation_model="llama",
                    value=["Do not apologize to the user."],
                    positive_examples=[],
                    negative_examples=["I'm sorry", "I apologize"],
                    token_limit=1024,
                    name="No Apologies"
                )
            ]
        )
        
        self.client.add_model(llama_model_config)
        self.client.add_model(simple_ai_config)
    
    def update_screen(self):
        if self.current_conversation:
            self.screen_should_update(self.session_id, self.current_conversation)
    
    def set_current_conversation(self, conv: Conversation):
        """Set the current active conversation."""
        self.current_conversation = conv
        def update_soon(self=self):
            import time
            time.sleep(2)
            self.update_screen()
        Thread(target=update_soon).start()
    
    def send_message(self, user_message: str):
        """Send a message to AI and get response asynchronously."""
        if not self.current_conversation:
            raise ValueError("No current conversation set")
        
        # Add user message
        user_msg = Message(role=Roles.USER, content=user_message)
        self.current_conversation.add_message(user_msg)
        self.current_conversation.save()
        self.update_screen()
        
        # Start async thread for AI response
        Thread(target=self._generate_ai_response).start()
    
    def _generate_ai_response(self):
        """Generate AI response using RequiredAI."""
        print(self.list)
        response = self.client.create_completion(
            model=self.current_model,
            messages=self.list
        )
        print("done generating\n\n")
        ai_msg = Message(
            role=Roles.ASSISTANT,
            content=response["choices"][0]["message"]["content"],
            model_name=self.current_model,
            extra={"raw": response}
        )
        print(ai_msg)
        self.current_conversation.add_message(ai_msg)
        self.current_conversation.save()
        
        self.update_screen()
        print("screen updated")
    
    @property
    def list(self) -> List[Dict[str, str]]:
        """Convert Conversation to RequiredAI message format."""
        return [
            {
                "role": msg.role.lower(),
                "content": msg.content
            }
            for msg in self.current_conversation.messages
        ]