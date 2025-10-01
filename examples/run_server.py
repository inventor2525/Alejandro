"""
Example script to run the RequiredAI server for Alejandro.
"""

import os
from pathlib import Path
from RequiredAI.server import RequiredAIServer
from Alejandro.Models.assistant_interaction_syntax import assistant_interaction_syntax
from Alejandro.Models.syntax_tree_requirement import SyntaxTreeValidatorRequirement

if __name__ == "__main__":
    # Path to the configuration file
    config_path = os.path.join(os.path.dirname(__file__), "server_config.json")
    
    # Create and run the server
    server = RequiredAIServer(config_path)
    server.run(host="0.0.0.0", port=5000, debug=True)