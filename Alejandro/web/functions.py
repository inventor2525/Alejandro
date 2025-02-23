from typing import Dict, Any, Optional, Type, Union, Callable, List
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.Core.screen_stack import ScreenStack

def navigate(screen_stack: ScreenStack, target_screen: Union[Type[Screen], Screen], **kwargs) -> Dict[str, Any]:
    """
    Navigate to a screen. Can take either:
    - A Screen type (will create new instance)
    - A Screen instance (will navigate directly to it)
    """
    if isinstance(target_screen, type):
        screen = target_screen(**kwargs)
    else:
        screen = target_screen
        
    screen_stack.push(screen)
    return {
        "navigate": screen.__class__.__name__.lower(),
        "force": True
    }

def go_back(screen_stack: ScreenStack) -> Dict[str, Any]:
    """Pop current screen and return to previous"""
    if screen_stack.pop():
        current = screen_stack.current
        return {
            "navigate": current.__class__.__name__.lower(),
            "force": True
        }
    return {}

def go_forward(screen_stack: ScreenStack) -> Dict[str, Any]:
    """Navigate forward in history if possible"""
    if screen_stack.forward():
        current = screen_stack.current
        return {
            "navigate": current.__class__.__name__.lower(),
            "force": True
        }
    return {}

# Control Factories
def make_back_control() -> Control:
    """Create a back navigation control"""
    return Control(
        id="back",
        text="Back",
        keyphrases=["back", "go back", "return"],
        action=lambda s=None: go_back(s) if s else {}
    )
