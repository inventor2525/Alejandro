from typing import Dict, Any, Optional, Type, Union, Callable, List
from Alejandro.Models.screen import Screen
from Alejandro.Models.control import Control
from Alejandro.Core.screen_stack import ScreenStack
from Alejandro.web.session import get_or_create_session
from Alejandro.web.events import NavigationEvent, push_event

def navigate(target_screen: Union[Type[Screen], Screen], session_id: Optional[str] = None) -> None:
    """Navigate to a screen"""
    
    if isinstance(target_screen, type):
        screen = target_screen()
    else:
        screen = target_screen
        
    session = get_or_create_session(session_id)
    session.core_app.screen_stack.push(screen)
    push_event(NavigationEvent(
        screen_type=type(screen)
    ))

def go_back() -> None:
    """Pop current screen and return to previous"""
    
    session = get_or_create_session()
    if session.screen_stack.pop():
        current = session.screen_stack.current
        push_event(NavigationEvent(
            screen_type=type(current)
        ))

def go_forward() -> None:
    """Navigate forward in history if possible"""
    
    session = get_or_create_session()
    if session.screen_stack.forward():
        current = session.screen_stack.current
        push_event(NavigationEvent(
            screen_type=type(current)
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
