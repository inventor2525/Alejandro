from typing import List, Optional, Dict, ClassVar, Any
from datetime import datetime
from RequiredAI.json_dataclass import json_dataclass, field, config, IDType
import uuid
import os

@json_dataclass(has_id=True, id_type=IDType.UUID, auto_id_name='id')
class Message:
	role: str
	content: str
	date_created: datetime = field(
		default_factory=datetime.now,
		metadata=config(
			encoder=lambda d: d.isoformat(),
			decoder=datetime.fromisoformat
		)
	)
	model_name: Optional[str] = None
	extra: Dict[str, Any] = field(default_factory=dict)
	parent: Optional["Message"] = None
	children: List["Message"] = field(default_factory=list)

class Roles:
	SYSTEM = "system"
	USER = "user"
	DEVELOPER = "developer"
	ASSISTANT = "assistant"

@json_dataclass(has_id=True, id_type=IDType.UUID, auto_id_name='id')
class Conversation:
	ROOT_DIRECTORY: ClassVar[str] = os.path.expanduser("~/Documents/Alejandro/Conversations")
	name: str = ""
	description: str = ""
	messages: List[Message] = field(default_factory=list)
	date_created: datetime = field(
		default_factory=datetime.now,
		metadata=config(
			encoder=lambda d: d.isoformat(),
			decoder=datetime.fromisoformat
		)
	)
	date_last_modified: datetime = field(
		default_factory=datetime.now,
		metadata=config(
			encoder=lambda d: d.isoformat(),
			decoder=datetime.fromisoformat
		)
	)

	def add_message(self, message_input: Message | str | tuple[str, str] | Dict[str, Any], parent: Optional[Message] = None) -> None:
		if isinstance(message_input, Message):
			message = message_input
		elif isinstance(message_input, str):
			message = Message(role=Roles.USER, content=message_input)
		elif isinstance(message_input, tuple):
			content, role = message_input
			message = Message(role=role, content=content)
		elif isinstance(message_input, dict):
			role = message_input.get('role', Roles.USER)
			content = message_input.get('content', '')
			model_name = message_input.get('model')
			extra = {k: v for k, v in message_input.items() if k not in ['role', 'content', 'model']}
			message = Message(role=role, content=content, model_name=model_name, extra=extra)
		else:
			raise ValueError("Invalid message input type")

		if parent:
			parent.children.append(message)
			message.parent = parent
		self.messages.append(message)
		self.date_last_modified = datetime.now()

	def save(self) -> None:
		path = os.path.join(self.ROOT_DIRECTORY, f"{self.id}.json")
		with open(path, "w") as f:
			f.write(self.to_json())

	@classmethod
	def load(cls, conv_id: str):
		path = os.path.join(cls.ROOT_DIRECTORY, f"{conv_id}.json")
		if not os.path.exists(path):
			raise FileNotFoundError(f"Conversation {conv_id} not found")
		with open(path, "r") as f:
			data = f.read()
		return cls.from_json(data)
	
	@property
	def short_id(self) -> str:
		def get_short_ids():
			if hasattr(Conversation, 'short_ids'):
				return Conversation.short_ids
			
			files = [f for f in os.listdir(Conversation.ROOT_DIRECTORY) if f.endswith('.json')]
			full_ids = [os.path.splitext(f)[0] for f in files]
			
			# Find minimal unique L chars for suffixes
			L = 4
			while True:
				suffixes = [id_[-L:] for id_ in full_ids]
				if len(set(suffixes)) == len(full_ids):
					break
				L += 1
			
			Conversation.short_ids = {id_: id_[-L:] for id_ in full_ids}
			return Conversation.short_ids
		
		return get_short_ids()[self.id]
			

os.makedirs(Conversation.ROOT_DIRECTORY, exist_ok=True)