from typing import List, Dict, Any, Optional, TYPE_CHECKING
from weakref import ref, ReferenceType
from Alejandro.Core.Control import Control

if TYPE_CHECKING:
    from Alejandro.web.session import Session
from RequiredAI.helpers import json_dataclass, field

@json_dataclass
class Screen:
    """
    Base screen class representing a distinct view in the application.
    Each screen has its own template, title, and set of controls.
    """
    model_config = {
        'arbitrary_types_allowed': True,
        'from_attributes': True
    }
    
    session: 'Session' = field(exclude=True)
    
    def __init__(self, session: 'Session', **data):
        session_ref = ref(session)
        super().__init__(session=session_ref, **data)
    title: str
    controls: List[Control] = []
    
    def get_template_data(self) -> Dict[str, Any]:
        """Get any additional template data needed for rendering"""
        return {}
    
    @classmethod
    def url(cls):
        url = cls.__name__.lower()
        if url.endswith('screen'):
            #remove screen from the end of the name:
            url = url[:-len("screen")]
        return url