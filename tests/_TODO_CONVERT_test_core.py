from datetime import datetime
from typing import List
import pytest
from Alejandro.Core.Control import Control, ControlResult
from Alejandro.Core.Screen import Screen
from Alejandro.Core.ScreenStack import ScreenStack
from Alejandro.Core.Application import Application
from Alejandro.Core.WordNode import WordNode
from Alejandro.Core.StringWordStream import StringWordStream
from Alejandro.Core.ModelControl import ModalControl, ModalState

class TestScreen(Screen):
    """Test screen implementation"""
    def __init__(self, title: str, controls: List[Control] = None):
        super().__init__(title=title, controls=controls or [])

def test_control():
    """Test Control validation and action"""
    action_called = False
    def test_action():
        nonlocal action_called
        action_called = True
    
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
    
    # Test matching phrase
    words = StringWordStream.process_text("run test")
    result = control.validate_word(words[1])  # "test"
    assert result == ControlResult.USED
    assert action_called

def test_screen_stack():
    """Test ScreenStack navigation"""
    welcome = TestScreen("Welcome")
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
    screen = TestScreen("Test", controls)
    
    # Create and run application
    app = Application(stream, screen)
    app.add_global_word_handler(global_handler)
    
    # Add test words
    stream.add_words("click the button")  # Should trigger control
    stream.add_words("more words")        # Should be received by global handler
    
    # Run app
    app.run()
    
    assert received_words == ["click", "the", "button", "more", "words"]
    assert action_called

def test_modal_control():
    """Test ModalControl state management and word collection"""
    control = ModalControl(
        text="Start Dictation",
        keyphrases=["start speaking"],
        deactivate_phrases=["stop speaking"],
        action=lambda: None
    )
    
    assert control.state == ModalState.INACTIVE
    assert len(control.collected_words) == 0
    
    # Test non-activation phrase
    word = WordNode(word="hello", start_time=datetime.now(), end_time=datetime.now())
    result = control.validate_word(word)
    assert result == ControlResult.UNUSED
    assert control.state == ModalState.INACTIVE
    
    # Test activation
    words = StringWordStream.process_text("start speaking")
    for word in words:
        result = control.validate_word(word)
    assert result == ControlResult.HOLD
    assert control.state == ModalState.HOLDING
    assert len(control.collected_words) == 0  # Activation phrase not collected
    
    # Test word collection
    words = StringWordStream.process_text("this is a test")
    for word in words:
        result = control.validate_word(word)
        assert result == ControlResult.HOLD
    assert len(control.collected_words) == 4
    assert [w.word for w in control.collected_words] == ["this", "is", "a", "test"]
    
    # Test deactivation
    words = StringWordStream.process_text("stop speaking")
    print("\nTesting deactivation phrase:")
    for word in words:
        print(f"Current collected words: {[w.word for w in control.collected_words]}")
        result = control.validate_word(word)
        print(f"Word: {word.word}, Result: {result}")
        print(f"Collected words: {[w.word for w in control.collected_words]}")
    
    assert control.state == ModalState.INACTIVE
    assert len(control.collected_words) == 4  # Deactivation phrase not collected
    assert [w.word for w in control.collected_words] == ["this", "is", "a", "test"]

def test_modal_control_application():
    """Test ModalControl integration with Application"""
    stream = StringWordStream()
    
    # Create modal control
    collected = []
    def on_complete():
        nonlocal collected
        collected = [w.word for w in control.collected_words]
        
    control = ModalControl(
        text="Start Dictation",
        keyphrases=["begin dictation"],
        deactivate_phrases=["end dictation"],
        action=on_complete
    )
    
    screen = TestScreen("Test", [control])
    app = Application(stream, screen)
    
    # Test full dictation sequence
    stream.add_words("begin dictation")        # Activate
    stream.add_words("this is some text")      # Collect
    stream.add_words("that should be saved")   # Collect
    stream.add_words("end dictation")          # Deactivate
    
    app.run()
    
    # Verify collected words
    expected = ["this", "is", "some", "text", "that", "should", "be", "saved"]
    assert collected == expected
