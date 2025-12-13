from typing import List, Optional, Callable, Dict, Any
from enum import Enum, auto
from Alejandro.Core.Signal import Signal
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.WordNode import WordNode
from RequiredAI.client import RequiredAIClient
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.Requirement import Requirements
from RequiredAI.json_dataclass import json_dataclass
from RequiredAI.ModelConfig import ModelConfig, InheritedModel, InputConfig
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Core.app_path import app_path
from threading import Thread
import json
import os
from dataclasses import dataclass

# Groq
llama_8b = ModelConfig(
	name="llama 8b 3.1",
	provider="groq",
	provider_model="llama-3.1-8b-instant"
)
llama_70b = ModelConfig(
	name="Llama 70b 3.3",
	provider="groq",
	provider_model="llama-3.3-70b-versatile"
)
gpt_oss_20b = ModelConfig(
	name="gpt-oss-20b",
	provider="groq",
	provider_model="openai/gpt-oss-20b"
)
gpt_oss_120b = ModelConfig(
	name="gpt-oss-120b",
	provider="groq",
	provider_model="openai/gpt-oss-120b"
)

# Anthropic
sonnet_37 = ModelConfig(
	name="Claude Sonnet 3.7",
	provider="anthropic",
	provider_model="claude-3-7-sonnet-20250219"
)
sonnet_45 = ModelConfig(
	name="Claude Sonnet 4.5",
	provider="anthropic",
	provider_model="claude-sonnet-4-5-20250929"
)
haiku_35 = ModelConfig(
	name="Claude Haiku 3.5",
	provider="anthropic",
	provider_model="claude-3-5-haiku-20241022"
)

# Gemini
gemini_pro = ModelConfig(
	name="Gemini 2.5 Pro",
	provider="gemini",
	provider_model="gemini-2.5-pro"
)
gemini_flash = ModelConfig(
	name="Gemini 2.5 Flash",
	provider="gemini",
	provider_model="gemini-2.5-flash"
)
gemini_flash_lite = ModelConfig(
	name="Gemini 2.5 Flash Lite",
	provider="gemini",
	provider_model="gemini-2.5-flash-lite"
)

# RequiredAI
talk = InheritedModel(
	name="Talk",
	base_model=llama_70b,
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not apologize to the user for any reason."],
			positive_examples=[],
			negative_examples=["I'm sorry", "I apologize", "Forgive me"],
			name="No Apologies"
		),
		WrittenRequirement(
			evaluation_model=gpt_oss_120b.name, #TODO: input config
			value=["Only explain things the user asked you to. Assume that the user is LITERALLY an all knowing god like savant with absolutely INSANE technical prowess and is testing YOUR intelligence. Do not bore with explanations of things you weren't asked."],
			positive_examples=["User: 'show me how to write a generator in python' Assistant: 'x = [v for v in range(0,5)]'"],
			negative_examples=[r"""User: 'show me how to write a generator in python' Assistant: 'Create a new python file called generator.py in your home directory, open it, paste the following "x = [v for v in range(0,5)]" inside it, save, and run it by calling python generator.py'"""],
			name="No over explaining"
		),
		WrittenRequirement(
			evaluation_model=gpt_oss_120b.name,
			value=["Don't be a suck up. No stroking of ego. No saying how the user was right. No acknowledging their skill, and do NOT tell them how they are smarter than you or were more right about anything than you in any way at all."],
			positive_examples=[],
			negative_examples=[],
			name="No kiss up"
		),
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not explain code that you have written. Doc strings and comments where appropriate are the ONLY thing that should be in your response when your response includes code."],
			positive_examples=[],
			negative_examples=[],
			name="No explaining codeblock contents",
			revision_model=gemini_pro.name
		)
	]
)

browse = InheritedModel(
	name="Browse",
	base_model=llama_70b,
	requirements=[
		WrittenRequirement(
			evaluation_model=gpt_oss_20b.name,
			value=["Do not apologize to the user for any reason."],
			positive_examples=[],
			negative_examples=["I'm sorry", "I apologize", "Forgive me"],
			name="No Apologies"
		)
	],
	input_config=InputConfig(
		messages_to_include=[
			(0,-1),
			""
		],
		filter_tags=['browse']
	)
)

client = RequiredAIClient(base_url="http://localhost:5432")

@json_dataclass
class Note:
	name:str
	description:str
	contents:str
	
	@property
	def absolute_path(self):
		return app_path("notes", self.name+'.json')
	
	@staticmethod
	def load_note(note_name:str) -> Optional['Note']:
		note_path = app_path("notes", note_name+'.json')
		try:
			d = json.load(open(note_path))
			return Note(note_name, d['description'], d['content'])
		except:
			return None
	
	@staticmethod
	def list_notes() -> List[str]:
		notes_dir = app_path("notes")
		return [
			os.path.splitext(f)[0] for f in os.listdir(notes_dir)
			if os.path.isfile(os.path.join(notes_dir, f))
			and f.endswith('.json')
		]
	
	def save(self):
		with open(self.absolute_path, 'w') as f:
			json.dump(self.to_dict(), f)
	
@dataclass
class FlowContext:
	data: Any = None
	spoken_phrase: str = None
	conversation: Conversation = None
	assistant: 'Assistant' = None

class Assistant:
	"""Manages AI conversations for a session."""
	
	def __init__(self, session_id: str):
		self.session_id = session_id
		self.screen_should_update = Signal[[str, Conversation], None]()
		self.current_conversation: Optional[Conversation] = None
		self.current_model = "Talk"
		self.flows: List[Flow] = []
		self.controls: List[Control] = []
		self._setup_flows()
	
	def _setup_flows(self):
		# Load Note Flow
		load_note = flow(self)
		@load_note.control(keyphrases=["open a note", "load a note", "open note"], deactivate_phrases=['finished', 'done', 'load'])
		def load_note_control(ctx: FlowContext) -> FlowContext:
			note = Note.load_note(ctx.spoken_phrase)
			if note:
				msg = Message(
					Roles.USER,
					f"# User Note '{note.name}'\n> Description: {note.description}\n{note.contents}"
				)
				msg.tag('notes')
				ctx.conversation.add_message(msg)
				ctx.assistant.update_screen()
			return ctx
		
		# New Note Flow
		new_note = flow(self)
		@new_note.control(keyphrases=["add a note", "make a note"], deactivate_phrases=['finished', 'done', 'save'])
		def new_note_control(ctx: FlowContext) -> FlowContext:
			ctx.data = ctx.spoken_phrase  # Content
			msg = Message(Roles.USER, ctx.data, tags=['note_content'])
			ctx.conversation.add_message(msg)
			return ctx
		
		new_note.model(base_model=llama_70b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_20b.name,
				value=["Only include the title, nothing else."],
				name="Title Only"
			)
		], input_config=InputConfig(messages_to_include=[
			{"role": "system", "content": "Generate a short, descriptive title for this note content."},
			(-1, -1)
		], filter_tags=['note_content']), output_tags=['note_title'])
		
		new_note.model(base_model=llama_70b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_20b.name,
				value=["Only include the description, nothing else."],
				name="Description Only"
			)
		], input_config=InputConfig(messages_to_include=[
			{"role": "system", "content": "Generate a concise description of the note content."},
			(-1, -1)
		], filter_tags=['note_content']), output_tags=['note_desc'])
		
		@new_note.code
		def save_note(ctx: FlowContext) -> FlowContext:
			title_msgs = InputConfig(filter_tags=['note_title']).select(ctx.conversation.messages)
			desc_msgs = InputConfig(filter_tags=['note_desc']).select(ctx.conversation.messages)
			content_msgs = InputConfig(filter_tags=['note_content']).select(ctx.conversation.messages)
			title = title_msgs[-1]['content'] if title_msgs else f"note_{len(Note.list_notes()) + 1}"
			desc = desc_msgs[-1]['content'] if desc_msgs else ""
			content = content_msgs[-1]['content'] if content_msgs else ""
			note = Note(title, desc, content)
			note.save()
			return ctx
		
		# Recall Note Flow
		recall_note = flow(self)
		@recall_note.control(keyphrases=["recall note", "find note"], deactivate_phrases=['done', 'finished'])
		def recall_note_control(ctx: FlowContext) -> FlowContext:
			ctx.data = ctx.spoken_phrase  # Description
			msg = Message(Roles.USER, ctx.data, tags=['recall_desc'])
			ctx.conversation.add_message(msg)
			return ctx
		
		recall_note.model(base_model=llama_70b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_20b.name,
				value=["Output only the note name, nothing else."],
				name="Name Only"
			)
		], input_config=InputConfig(messages_to_include=[
			{"role": "system", "content": "Find the note name that best matches this description."},
			(-1, -1)
		], filter_tags=['recall_desc', 'notes']), output_tags=['recalled_note_name'])
		
		@recall_note.code
		def load_note(ctx: FlowContext) -> FlowContext:
			name_msgs = InputConfig(filter_tags=['recalled_note_name']).select(ctx.conversation.messages)
			note_name = name_msgs[-1]['content'] if name_msgs else None
			if note_name:
				note = Note.load_note(note_name)
				if note:
					msg = Message(
						Roles.USER,
						f"# Recalled Note '{note.name}'\n> Description: {note.description}\n{note.contents}"
					)
					msg.tag('notes')
					ctx.conversation.add_message(msg)
					ctx.assistant.update_screen()
			return ctx
		
		# Setup all flows
		for f in self.flows:
			f.setup_all()
	
	def update_screen(self):
		if self.current_conversation:
			self.screen_should_update(self.session_id, self.current_conversation)
	
	def set_current_conversation(self, conv: Conversation):
		"""Set the current active conversation."""
		self.current_conversation = conv
	
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
		response = client.create_completion(
			model=self.current_model,
			messages=self.list
		)
		
		ai_msg = Message(
			role=Roles.ASSISTANT,
			content=response["choices"][0]["message"]["content"],
			model_name=self.current_model,
			extra={"raw": response},
			tags=response.get('tags',[])
		)
		
		self.current_conversation.add_message(ai_msg)
		self.current_conversation.save()
		
		self.update_screen()
	
	@property
	def list(self) -> List[Dict[str, str]]:
		"""Convert Conversation to RequiredAI message format."""
		msg_list = []
		for msg in self.current_conversation.messages:
			md = {
				"role": msg.role.lower(),
				"content": msg.content
			}
			if msg.tags:
				md['tags'] = msg.tags
			msg_list.append(md)
		return msg_list
	
# Flow system
@dataclass
class Flow:
	assistant: 'Assistant'
	
	prev: 'Flow' = None
	next: 'Flow' = None
	
	def setup(self):
		pass
	
	def setup_all(self):
		n = self
		while n:
			n.setup()
			n = n.next
	
	def __call__(self, ctx: FlowContext) -> FlowContext:
		current = self
		while current:
			ctx = current.action(ctx)
			current = current.next
		return ctx
	
	def action(self, ctx: FlowContext) -> FlowContext:
		return ctx
	
	def control(self, keyphrases: List[str] = [], deactivate_phrases: List[str] = None) -> Callable[[Callable[[FlowContext], FlowContext]], Callable[[FlowContext], FlowContext]]:
		def inner(action: Callable[[FlowContext], FlowContext], keyphrases=keyphrases, deactivate_phrases=deactivate_phrases):
			control_flow = ControlFlow(
				assistant=self.assistant,
				keyphrases=keyphrases,
				deactivate_phrases=deactivate_phrases,
				action=action
			)
			self.assistant.flows.append(control_flow)
			return action
		return inner
	
	def model(self, base_model: ModelConfig, requirements: List[Requirement] = [], input_config: InputConfig = None, output_tags: List[str] = []):
		model_flow = ModelFlow(
			assistant=self.assistant,
			base_model=base_model,
			requirements=requirements,
			input_config=input_config,
			output_tags=output_tags
		)
		self.assistant.flows.append(model_flow)
	
	def code(self) -> Callable[[Callable[[FlowContext], FlowContext]], Callable[[FlowContext], FlowContext]]:
		def inner(action: Callable[[FlowContext], FlowContext]):
			code_flow = CodeFlow(
				assistant=self.assistant,
				action=action
			)
			self.assistant.flows.append(code_flow)
			return action
		return inner

@dataclass
class ControlFlow(Flow):
	keyphrases: List[str] = field(default_factory=list)
	deactivate_phrases: List[str] = None
	action: Callable[[FlowContext], FlowContext] = None
	
	def __call__(self, ctx: FlowContext) -> FlowContext:
		ctx = self.action(ctx)
		if self.next:
			return self.next(ctx)
		return ctx
	
	def setup(self):
		control_cls = ModalControl if self.deactivate_phrases else Control
		ctrl = control_cls(
			id=id(self),
			text="Activate Flow",
			keyphrases=self.keyphrases,
			deactivate_phrases=self.deactivate_phrases,
			action=lambda control: self(FlowContext(
				data=control.collected_words if isinstance(control, ModalControl) else None,
				spoken_phrase=control.collected_words if isinstance(control, ModalControl) else None,
				conversation=self.assistant.current_conversation,
				assistant=self.assistant
			))
		)
		self.assistant.controls.append(ctrl)

@dataclass
class ModelFlow(Flow):
	base_model: ModelConfig
	requirements: List[Requirement] = field(default_factory=list)
	input_config: InputConfig = None
	output_tags: List[str] = field(default_factory=list)
	
	def __call__(self, ctx: FlowContext) -> FlowContext:
		ctx = self.action(ctx)
		if self.next:
			return self.next(ctx)
		return ctx
	
	def setup(self):
		model = InheritedModel(
			name=id(self),
			base_model=self.base_model,
			requirements=self.requirements,
			input_config=self.input_config,
			output_tags=self.output_tags
		)
		client.add_model(model)
	
	def action(self, ctx: FlowContext) -> FlowContext:
		input_msgs = self.input_config.select(ctx.conversation.messages) if self.input_config else []
		if ctx.data:
			input_msgs.append({"role": "user", "content": ctx.data})
		response = client.create_completion(id(self), input_msgs)
		content = response["choices"][0]["message"]["content"]
		msg = Message(Roles.ASSISTANT, content, tags=self.output_tags)
		ctx.conversation.add_message(msg)
		ctx.data = content
		return ctx

@dataclass
class CodeFlow(Flow):
	action: Callable[[FlowContext], FlowContext] = None
	
	def __call__(self, ctx: FlowContext) -> FlowContext:
		ctx = self.action(ctx)
		if self.next:
			return self.next(ctx)
		return ctx
	

def flow(assistant: Assistant) -> Flow:
	return Flow(assistant=assistant)