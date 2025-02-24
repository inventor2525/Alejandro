from typing import List, Dict, Any, Optional, TYPE_CHECKING
from weakref import ref, ReferenceType
from pydantic import BaseModel, Field
from Alejandro.Models.control import Control

if TYPE_CHECKING:
    from Alejandro.web.session import Session

class Screen(BaseModel):
    """
    Base screen class representing a distinct view in the application.
    Each screen has its own template, title, and set of controls.
    """
    model_config = {
        'arbitrary_types_allowed': True,
        'from_attributes': True
    }
    
    title: str
    controls: List[Control] = []
    enter_count: int = Field(default=0)
    exit_count: int = Field(default=0)
    session: Optional[ReferenceType['Session']] = Field(default=None, exclude=True)
    
    def get_session(self) -> Optional['Session']:
        """Get session safely from weak reference"""
        return self.session() if self.session is not None else None
    
    def on_enter(self) -> None:
        """Called when this screen becomes active"""
        self.enter_count += 1
        
    def on_exit(self) -> None:
        """Called when navigating away from this screen"""
        self.exit_count += 1
        
    def get_template_data(self) -> Dict[str, Any]:
        """Get any additional template data needed for rendering"""
        return {}
