# OnScreenRobot - Expanded Features

## New Capability: System Control

The robot can now control your PC! You can ask it to open common applications.

### Supported Voice Commands

Try saying these commands:

- "Open Calculator"
- "Open Notepad"
- "Open Paint"
- "Open Chrome"
- "Open Edge"
- "Open Control Panel"
- "Open Command Prompt"

### How it works

1. **Speech Recognition**: The enhanced `listen.ps1` script now listens specifically for these app commands.
2. **AI Processing**: The Local Brain (Llama3/Ollama) interprets your intent and sends a special `[OPEN: app_name]` tag.
3. **Execution**: The Python backend triggers the application launch instantly.

## Setup

1. Ensure you have **Ollama** running with `llama3`.
2. Run the python brain: `python brain.py`
3. Run the electron app: `npm start`
