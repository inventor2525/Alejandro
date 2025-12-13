from typing import List, Optional, Callable, Dict
from enum import Enum, auto
from Alejandro.Core.Signal import Signal
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.WordNode import WordNode
from RequiredAI.helpers import get_msg_content
from RequiredAI.client import RequiredAIClient
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.Requirement import Requirements
from RequiredAI.json_dataclass import json_dataclass
from RequiredAI.ModelConfig import ModelConfig, InheritedModel, InputConfig
from Alejandro.Core.Screen import control
from Alejandro.Models.Conversation import Conversation, Message, Roles
from Alejandro.Core.ModalControl import ModalControl
from Alejandro.Core.Control import Control
from Alejandro.Core.app_path import app_path
from threading import Thread
import json
import os

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
	
class Assistant:
	"""Manages AI conversations for a session."""
	
	def __init__(self, session_id: str):
		self.session_id = session_id
		self.screen_should_update = Signal[[str, Conversation], None]()
		self.current_conversation: Optional[Conversation] = None
		self.current_model = "Talk"
	
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
			content=get_msg_content(response),
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

#WIP global controls.... get them with the get_controls method in Screen.py:
	@control(keyphrases=["open a note", "load a note", "open note"], deactivate_phrases=['finished', 'done', 'load'])
	def load_note(self, control: ModalControl):
		name = control.collected_words
		note = Note.load_note(name)
		if note:
			msg = Message(
				Roles.USER,
				f"# User Note '{note.name}'\n> Description: {note.description}\n{note.contents}"
			)
			msg.tag('notes')
			self.current_conversation.add_message(msg)
			self.update_screen()

	@control(keyphrases=["add a note", 'make a note'], deactivate_phrases=['finished', 'done', 'save'])
	def save_note(self, control: ModalControl):
		collected_text = control.collected_words
		name_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Generate a concise, unique filename for the note based on its content. Output only the filename."],
				name="Note Name Generator"
			)
		])
		desc_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Generate a short description of the note content. Output only the description."],
				name="Note Description Generator"
			)
		])

		name_response = name_model([{"role": "user", "content": collected_text}])
		note_name = get_msg_content(name_response).strip()

		desc_response = desc_model([{"role": "user", "content": collected_text}])
		note_desc = get_msg_content(desc_response).strip()

		note = Note(name=note_name, description=note_desc, contents=collected_text)
		note.save()

	@control(keyphrases=["search notes"], deactivate_phrases=['finished', 'done'])
	def search_notes(self, control: ModalControl):
		search_text = control.collected_words
		notes = Note.list_notes()
		compare_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Determine if the note matches the search query. Respond with 'yes' or 'no' only."],
				name="Note Comparator"
			)
		])
		rank_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Rank the notes by relevance to the query, output sorted list of note names only, one per line."],
				name="Note Ranker"
			)
		])

		matching_notes = []
		for note_name in notes:
			note = Note.load_note(note_name)
			compare_response = compare_model([{"role": "user", "content": f"Query: {search_text}\nNote: {note.contents}"}])
			if "yes" in get_msg_content(compare_response).lower():
				matching_notes.append(note)

		if not matching_notes:
			return

		note_contents = "\n".join([f"{note.name}: {note.contents}" for note in matching_notes])
		rank_response = rank_model([{"role": "user", "content": f"Query: {search_text}\nNotes:\n{note_contents}"}])
		ranked_names = [line.strip() for line in get_msg_content(rank_response).split("\n") if line.strip()]

		if ranked_names:
			top_note_name = ranked_names[0]
			self.load_note(top_note_name)

	@control(keyphrases=["find note"], deactivate_phrases=['finished', 'done'])
	def find_note(self, control: ModalControl):
		search_text = control.collected_words
		notes = Note.list_notes()
		compare_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Determine if the note name or description matches the search query. Respond with 'yes' or 'no' only."],
				name="Note Finder Comparator"
			)
		])
		rank_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=llama_8b.name,
				value=["Rank the notes by relevance to the query based on name and description, output sorted list of note names only, one per line."],
				name="Note Finder Ranker"
			)
		])

		matching_notes = []
		for note_name in notes:
			note = Note.load_note(note_name)
			compare_response = compare_model([{"role": "user", "content": f"Query: {search_text}\nName: {note.name}\nDescription: {note.description}"}])
			if "yes" in get_msg_content(compare_response).lower():
				matching_notes.append(note)

		if not matching_notes:
			return

		note_info = "\n".join([f"{note.name}: {note.description}" for note in matching_notes])
		rank_response = rank_model([{"role": "user", "content": f"Query: {search_text}\nNotes:\n{note_info}"}])
		ranked_names = [line.strip() for line in get_msg_content(rank_response).split("\n") if line.strip()]

		if ranked_names:
			top_note_name = ranked_names[0]
			self.load_note(top_note_name)