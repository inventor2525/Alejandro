from flask import Blueprint, render_template, request
from RequiredAI.RequirementTypes import WrittenRequirement
from RequiredAI.helpers import get_msg_content
from Alejandro.Models.Conversation import Message, Conversation, Roles
from Alejandro.Models.Note import Note
from Alejandro.Core.Assistant import client, gpt_oss_120b
from Alejandro.web.session import get_or_create_session, Session
from Alejandro.Core.Screen import Screen, screen_type, control, ModalControl
from Alejandro.Core.Control import Control
bp = Blueprint('notes', __name__)

@screen_type
class NotesScreen(Screen):
	def __init__(self, session: 'Session'):
		from Alejandro.web.blueprints.conversations import ConversationsScreen
		from Alejandro.web.blueprints.terminal import TerminalScreen
		from Alejandro.web.blueprints.notes import NotesScreen
		super().__init__(
			session=session,
			title="Notes",
			controls=[
				session.make_back_control()
			])
	
	@control(keyphrases=["load note", "open a note", "load a note", "open note"], deactivate_phrases=['finished', 'done', 'load'])
	def load_note(self, control: ModalControl):
		name = control.collected_words
		note = Note.load_note(name)
		print(f"loaded note:{str(note)}")
		if note:
			msg = Message(
				Roles.USER,
				f"# User Note '{note.name}'\n> Description: {note.description}\n```txt\n{note.contents}\n```"
			)
			msg.tag('notes')
			self.session.conversation_manager.current_conversation.add_message(msg)
			self.session.conversation_manager.update_screen()

	@control(keyphrases=["save note", "add a note", "make a note", "create note"], deactivate_phrases=['finished', 'done', 'save'])
	def save_note(self, control: ModalControl):
		collected_text = control.collected_words
		name_model = client.model(base_model=gpt_oss_120b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Keep the name short"],
				name="Short couple word names."
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Do not respond with any text other than the name."],
				negative_examples=["Ok, here is the name you requested...", "Sure thing...", "... Is there anything else you would like?"],
				name="No conversing the user."
			)
		])
		desc_model = client.model(base_model=gpt_oss_120b, requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Keep the description to at most 1 paragraph, 5 sentences or less."],
				name="Brief descriptive summary."
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Do not respond with any text other than the description."],
				negative_examples=["Ok, here is the description you requested...", "Sure thing...", "... Is there anything else you would like?"],
				name="No conversing the user."
			),
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Include only a summary of the note, without waisting words mentioning it is a note."],
				positive_examples=["Remember to pick up pears apples and oranges."],
				negative_examples=["A note about a shopping list for pears apples and oranges"],
				name="First person."
			),
		])

		name_response = name_model(f"Come up with a brief descriptive name for this note the user just took:\n```txt\n{collected_text}\n```")
		note_name = get_msg_content(name_response).strip()

		desc_response = desc_model(f"Come up with a brief description for this note the user just took:\n```txt\n{collected_text}\n```")
		note_desc = get_msg_content(desc_response).strip()

		note = Note(name=note_name, description=note_desc, contents=collected_text)
		print("Saving note...", str(note))
		note.save()

	@control(keyphrases=["search notes"], deactivate_phrases=['finished', 'done'])
	def search_notes(self, control: ModalControl):
		search_text = control.collected_words
		notes = Note.list_notes()
		compare_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
				value=["Determine if the note matches the search query. Respond with 'yes' or 'no' only."],
				name="Note Comparator"
			)
		])
		rank_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
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
				evaluation_model=gpt_oss_120b.name,
				value=["Determine if the note name or description matches the search query. Respond with 'yes' or 'no' only."],
				name="Note Finder Comparator"
			)
		])
		rank_model = client.model(requirements=[
			WrittenRequirement(
				evaluation_model=gpt_oss_120b.name,
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

@bp.route(f'/{NotesScreen.url()}')
def show_screen() -> str:
	"""Generic screen route handler"""
	session_id = request.args.get('session')
		
	session = get_or_create_session(session_id)
	screen = session.current_or_get(NotesScreen)
	return render_template(
		'base.html',
		screen=screen,
		session_id=session.id,
		**screen.get_template_data()
	)
