from datetime import datetime
from typing import List
import pytest
from Alejandro.Models.control import Control, ControlResult
from Alejandro.Models.modal_control import ModalControl
from Alejandro.Models.screen import Screen
from Alejandro.Core.screen_stack import ScreenStack
from Alejandro.Core.application import Application
from Alejandro.Models.word_node import WordNode
from Alejandro.Core.string_word_stream import StringWordStream

def test_control():
    """Test Control validation and action"""
    action_called = False
    def test_action():
        nonlocal action_called
        action_called = True
        
    # Create control with multiple keyphrases
    control = Control(
        text="Test Button",
        keyphrases=["run test", "execute test"],
        action=test_action
    )
    
    # Test non-matching word
    result = control.validate_word(WordNode(
        word="hello",
        start_time=datetime.now(),
        end_time=datetime.now()
    ))
    assert result == ControlResult.UNUSED
    assert not action_called
    
    # Create linked words "run test"
    words = StringWordStream().process_text("run test")
    
    # Test matching phrase
    result = control.validate_word(words[1])  # "test"
    assert result == ControlResult.USED
    assert action_called

def test_screen_stack():
    """Test ScreenStack navigation"""
    class TestScreen(Screen):
        """Test screen implementation"""
        def __init__(self, title: str, controls: List[Control] = None):
            super().__init__(title=title, controls=controls or [])
            
    welcome = TestScreen(title="Welcome")
    main = TestScreen("Main") 
    settings = TestScreen("Settings")
    
    stack = ScreenStack(welcome)
    assert stack.current == welcome
    assert welcome.enter_count == 1
    
    # Test push
    stack.push(main)
    assert stack.current == main
    assert welcome.exit_count == 1
    assert main.enter_count == 1
    
    stack.push(settings)
    assert stack.current == settings
    assert main.exit_count == 1
    assert settings.enter_count == 1
    
    # Test pop
    popped = stack.pop()
    assert popped == settings
    assert stack.current == main
    assert settings.exit_count == 1
    assert main.enter_count == 2
    
    # Test forward
    assert stack.forward()
    assert stack.current == settings
    assert settings.enter_count == 2
    
    # Test pop at root
    stack = ScreenStack(welcome)
    assert stack.pop() is None
    assert stack.current == welcome

def test_application():
    """Test Application word processing"""
    stream = StringWordStream()
    
    # Track words received by global handler
    received_words = []
    def global_handler(word: str):
        received_words.append(word)
        
    # Create test screen with controls
    action_called = False
    def test_action():
        nonlocal action_called
        action_called = True
        
    controls = [
        Control(text="Test Button", keyphrases=["click"], action=test_action)
    ]
    class TestScreen(Screen):
        """Test screen implementation"""
        def __init__(self, title: str, controls: List[Control] = None):
            super().__init__(title=title, controls=controls or [])
            
    screen = TestScreen(title="Test", controls=controls)
    
    # Create and run application
    app = Application(stream, screen)
    app.add_global_word_handler(global_handler)
    
    # Add test words
    stream.add_words("click the button")  # Should trigger control
    stream.add_words("more words")        # Should be received by global handler
    
    # Run app
    app.run()
    
    # Verify global handler got all words
    assert received_words == [
        "click", "the", "button",
        "more", "words"
    ]
    
    # Verify action was called
    assert action_called

class TestScreen(Screen):
    """Test screen implementation"""
    def __init__(self, title: str, controls: List[Control] = None):
        super().__init__(title=title, controls=controls or [])

def test_modal_control():
    """Test ModalControl state management"""
    stream = StringWordStream()
    
    # Track modal state
    modal_entered = False
    modal_exited = False
    
    def on_enter():
        nonlocal modal_entered
        modal_entered = True
        
    def on_exit():
        nonlocal modal_exited
        modal_exited = True
    
    # Create modal control
    control = ModalControl(
        text="Start Dictation",
        keyphrases=["begin dictation", "start speaking"],
        deactivate_phrases=["end dictation", "stop speaking"],
        action=on_enter
    )
    
    # Create screen with modal control
    screen = TestScreen(title="Test", controls=[control])
    
    # Create and run application
    app = Application(stream, screen)
    
    # Test modal activation and deactivation
    stream.add_words("start speaking now")  # Should activate modal
    stream.add_words("some dictated text")  # Should pass through
    stream.add_words("end dictation")       # Should deactivate modal
    
    app.run()
    
    assert modal_entered
    assert not modal_exited  # Modal exit doesn't call action
