from typing import List, Dict, Any, Optional, TYPE_CHECKING, ClassVar, Type, TypeVar
from weakref import ref, ReferenceType
from Alejandro.Core.Control import Control
from Alejandro.Core.ModalControl import ModalControl
from dataclasses import dataclass

if TYPE_CHECKING:
	from Alejandro.web.session import Session
from RequiredAI.json_dataclass import *

@json_dataclass
class Screen:
	"""
	Base screen class representing a distinct view in the application.
	Each screen has its own template, title, and set of controls.
	"""
	session: 'Session' = field(metadata=config(exclude=True))
	
	title: str
	controls: List[Control] = field(default_factory=list)
	
	types: ClassVar[Dict[str, Type['Screen']]] = {}
	def get_template_data(self) -> Dict[str, Any]:
		"""Get any additional template data needed for rendering"""
		return {}
	
	@classmethod
	def url(cls) -> str:
		url = cls.__name__.lower()
		if url.endswith('screen'):
			#remove screen from the end of the name:
			url = url[:-len("screen")]
		return url
	
	def __post_init__(self):
		self.controls.extend( get_controls(self) )
	
T = TypeVar('T')
def screen_type(cls:Type[T]) -> Type[T]:
	Screen.types[cls.url()] = cls
	return cls

def control(text: Optional[str] = None, keyphrases: List[str] = [], deactivate_phrases: List[str] = [], js_getter_function: Optional[str] = None, js_return_handler: Optional[str] = None):
	def decorator(method, text=text, keyphrases=keyphrases, deactivate_phrases=deactivate_phrases, js_getter_function=js_getter_function, js_return_handler=js_return_handler):
		if not text:
			assert len(keyphrases)>0, 'Must have at least 1 key phrase if text is not passed'
			text = keyphrases[0]
			keyphrases = keyphrases[1:]
		method._control_config = {
			'text': text,
			'keyphrases': keyphrases,
			'js_getter_function': js_getter_function,
			'js_return_handler': js_return_handler
		}
		if deactivate_phrases:
			method._control_config['deactivate_phrases'] = deactivate_phrases
		return method
	return decorator

def get_controls(obj:Any) -> List[Control]:
	'''
	Gets all control decorated methods on the
	passed object and returns a list of Control
	objects that reflects those methods.
	'''
	controls = []
	for attr_name in dir(obj):
		attr = getattr(obj, attr_name)
		if callable(attr) and hasattr(attr, '_control_config'):
			control_type = ModalControl if 'deactivate_phrases' in attr._control_config else Control
			attr._control_config['id'] = attr_name
			attr._control_config['action'] = attr
			control_instance = control_type( **attr._control_config )
			controls.append(control_instance)
	return controls