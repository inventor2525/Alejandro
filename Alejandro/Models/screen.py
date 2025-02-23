from typing import List, Dict, Any
from pydantic import BaseModel
from Alejandro.Models.control import Control

class Screen(BaseModel):
    """
    Base screen class representing a distinct view in the application.
    Each screen has its own template, title, and set of controls.
    """
    title: str
    controls: List[Control] = []
    
    def on_enter(self) -> None:
        """Called when this screen becomes active"""
        pass
        
    def on_exit(self) -> None:
        """Called when navigating away from this screen"""
        pass
        
    def get_template_data(self) -> Dict[str, Any]:
        """Get any additional template data needed for rendering"""
        return {}
