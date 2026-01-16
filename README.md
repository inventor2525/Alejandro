# Alejandro

A voice-controlled interface framework that enables natural language interaction with applications through a combination of speech recognition and large language models.

## Core Features

- Abstract word stream interface for speech-to-text integration
- Screen-based navigation system with voice-activated controls
- Support for modal voice controls and complex interaction patterns
- Web interface with real-time transcription display
- Terminal integration capabilities
- Conversation management with LLM integration

## Installation

Optionally provide your ngrok token:
```bash
wget -O - https://raw.githubusercontent.com/inventor2525/Alejandro/claude/review-app-context-4TwcN/installer.sh | bash -s YOUR_NGROK_TOKEN
```

**Note:** This README currently points to the `claude/review-app-context-4TwcN` branch which includes:
- ClaudeCodeScreen: Voice-controlled Claude Code CLI interface
- BrainDumpScreen: Offline voice-to-file note-taking

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details
