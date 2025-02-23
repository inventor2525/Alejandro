from typing import Dict, Any, Optional, Type, Union
from Alejandro.Models.screen import Screen

def navigate(target_screen: Union[Type[Screen], Screen], **kwargs) -> Dict[str, Any]:
    """
    Navigate to a screen. Can take either:
    - A Screen type (will create new instance)
    - A Screen instance (will navigate directly to it)
    """
    from Alejandro.web.app import core_app
    
    if isinstance(target_screen, type):
        screen = target_screen(**kwargs)
    else:
        screen = target_screen
        
    core_app.screen_stack.push(screen)
    return {
        "navigate": screen.__class__.__name__.lower(),
        "force": True
    }

def go_back() -> Dict[str, Any]:
    """Pop current screen and return to previous"""
    from Alejandro.web.app import core_app
    
    if core_app.screen_stack.pop():
        current = core_app.screen_stack.current
        return {
            "navigate": current.__class__.__name__.lower(),
            "force": True
        }
    return {}

def go_forward() -> Dict[str, Any]:
    """Navigate forward in history if possible"""
    from Alejandro.web.app import core_app
    
    if core_app.screen_stack.forward():
        current = core_app.screen_stack.current
        return {
            "navigate": current.__class__.__name__.lower(),
            "force": True
        }
    return {}
