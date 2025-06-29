"""
Example of using the RequiredAI client with SmartModel.
"""

from RequiredAI.client import RequiredAIClient
from smart_model import smart_model_config, readme_content
from Alejandro.Models.assistant_interaction_syntax import assistant_interaction_syntax
from Alejandro.Models.syntax_tree_requirement import SyntaxTreeValidatorRequirement
import json

if __name__ == "__main__":
    # Create a client
    client = RequiredAIClient(
        base_url="http://localhost:5000"
    )
    
    # Send the SmartModel configuration to the server
    response = client.add_model(smart_model_config)
    print("Add SmartModel Response:", response)
    
    # Create a completion with the SmartModel
    response = client.create_completion(
        model="SmartModel",
        messages=[
            {"role": "system", "content": readme_content},
            {"role": "user", "content": "Write an AI script to create a new Python file and initialize a git repository."}
        ],
        max_tokens=1024
    )
    
    print("Final Response:")
    print(response["choices"][0]["message"]["content"])