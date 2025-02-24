from typing import Dict, Any, Optional, Type, Union, Callable, List
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.Core.screen_stack import ScreenStack

def navigate(target_screen: Union[Type[Screen], Screen]) -> None:
    """Navigate to a screen"""
    from Alejandro.web.app import core_app, action_queue
    
    if isinstance(target_screen, type):
        screen = target_screen()
    else:
        screen = target_screen
        
    core_app.screen_stack.push(screen)
    action_queue.put({
        "navigate": screen.__class__.__name__.lower(),
        "force": True
    })

def go_back() -> None:
    """Pop current screen and return to previous"""
    from Alejandro.web.app import core_app, action_queue
    
    if core_app.screen_stack.pop():
        current = core_app.screen_stack.current
        action_queue.put({
            "navigate": current.__class__.__name__.lower(),
            "force": True
        })

def go_forward() -> None:
    """Navigate forward in history if possible"""
    from Alejandro.web.app import core_app, action_queue
    
    if core_app.screen_stack.forward():
        current = core_app.screen_stack.current
        action_queue.put({
            "navigate": current.__class__.__name__.lower(),
            "force": True
        })

# Control Factories
def make_back_control() -> Control:
    """Create a back navigation control"""
    return Control(
        id="back",
        text="Back",
        keyphrases=["back", "go back", "return"],
        action=go_back
    )
