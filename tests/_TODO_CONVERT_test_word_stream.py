from Alejandro.Core.string_word_stream import StringWordStream

def test_word_stream():
    """Test the StringWordStream implementation"""
    stream = StringWordStream()
    
    # Test process_text
    nodes = stream.process_text("Hello World")
    assert len(nodes) == 2
    assert nodes[0].word == "hello"
    assert nodes[0].next == nodes[1]
    assert nodes[1].prev == nodes[0]
    assert nodes[1].word == "world"
    
    # Test streaming
    stream.start_listening()
    stream.add_words("Testing the stream")
    
    words = []
    for word in stream.words():
        words.append(word.word)
    
    assert words == ["testing", "the", "stream"]
    
    stream.stop_listening()
