from typing import List, Optional
from Alejandro.Core.app_path import app_path
from RequiredAI.json_dataclass import json_dataclass
import json
import os

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
	
	def __str__(self):
		desc = self.description.replace("\n","\n> ")
		return f"Note \"{self.name}\":\n> {desc}\n```txt\n{self.contents}\n```"