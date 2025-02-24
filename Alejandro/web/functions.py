from typing import Dict, Any, Optional, Type, Union, Callable, List
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.Core.screen_stack import ScreenStack

def navigate(target_screen: Union[Type[Screen], Screen]) -> None:
    """Navigate to a screen"""
    from Alejandro.web.session import core_app
    from Alejandro.web.events import NavigationEvent, push_event
    
    if isinstance(target_screen, type):
        screen = target_screen()
    else:
        screen = target_screen
        
    core_app.screen_stack.push(screen)
    push_event(NavigationEvent(
        screen_name=screen.__class__.__name__.lower()
    ))

def go_back() -> None:
    """Pop current screen and return to previous"""
    from Alejandro.web.session import core_app
    from Alejandro.web.events import NavigationEvent, push_event
    
    if core_app.screen_stack.pop():
        current = core_app.screen_stack.current
        push_event(NavigationEvent(
            screen_name=current.__class__.__name__.lower()
        ))

def go_forward() -> None:
    """Navigate forward in history if possible"""
    from Alejandro.web.session import core_app
    from Alejandro.web.events import NavigationEvent, push_event
    
    if core_app.screen_stack.forward():
        current = core_app.screen_stack.current
        push_event(NavigationEvent(
            screen_name=current.__class__.__name__.lower()
        ))

# Control Factories
def make_back_control() -> Control:
    """Create a back navigation control"""
    return Control(
        id="back",
        text="Back",
        keyphrases=["back", "go back", "return"],
        action=go_back
    )
