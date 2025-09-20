from typing import List, Dict, Any, Optional, TYPE_CHECKING, ClassVar, Type, TypeVar
from weakref import ref, ReferenceType
from Alejandro.Core.Control import Control

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
	
T = TypeVar('T')
def screen_type(cls:Type[T]) -> Type[T]:
	Screen.types[cls.url()] = cls
	return cls