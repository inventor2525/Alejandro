"""
Definition of the SmartModel for RequiredAI.
"""

from RequiredAI.models import *
from RequiredAI.requirements import *
from Alejandro.Models.assistant_interaction_syntax import assistant_interaction_syntax
from Alejandro.Models.syntax_tree_requirement import SyntaxTreeValidatorRequirement, SyntaxTreeNode
from RequiredAI.ModelConfig import ModelConfig

# Read the README content
README_PATH = "/home/charlie/Projects/Alejandro_dev/assistant_interaction/README.md"
with open(README_PATH, 'r') as f:
    readme_content = f.read()

def find_syntax_node(
    nodes: List[SyntaxTreeNode],
    start_regex: Optional[str] = None,
    end_regex: Optional[str] = None,
    validate_start_regex: Optional[str] = None,
    validate_end_regex: Optional[str] = None
) -> Optional[SyntaxTreeNode]:
    """
    Search for a SyntaxTreeNode matching the specified parameters using a non-recursive approach.
    
    Args:
        nodes: List of SyntaxTreeNode to search
        start_regex: Optional start regex to match
        end_regex: Optional end regex to match
        validate_start_regex: Optional validate start regex to match
        validate_end_regex: Optional validate end regex to match
    
    Returns:
        The matching SyntaxTreeNode or None if not found
    """
    import uuid
    open_list = list(nodes)
    closed_set = set()
    
    while open_list:
        node = open_list.pop(0)
        
        # Assign UUID if not present
        if not hasattr(node, '__uuid__'):
            node.__uuid__ = str(uuid.uuid4())
        
        # Skip if node has been visited
        elif node.__uuid__ in closed_set:
            continue
        
        # Check if node matches all provided conditions
        match = True
        if start_regex and node.start_regex != start_regex:
            match = False
        if end_regex and node.end_regex != end_regex:
            match = False
        if validate_start_regex and node.validate_start_regex != validate_start_regex:
            match = False
        if validate_end_regex and node.validate_end_regex != validate_end_regex:
            match = False
        
        if match:
            return node
        
		# Mark node as visited
        closed_set.add(node.__uuid__)
        
        # Add children to open_list
        open_list.extend(node.children)
    
    return None

# Find the bash node
bash_node = find_syntax_node(
    assistant_interaction_syntax,
    start_regex=r"^\s*### AI_BASH_START.*$"
)

if bash_node:
    bash_node.requirements.extend([
        WrittenRequirement(
            evaluation_model="llama3.3 70b",
            value=["Do not include git push commands."],
            positive_examples=["# Comment: User should run 'git push' when ready"],
            negative_examples=["git push origin main"],
            token_limit=1024,
            name="No Git Push"
        ),
        WrittenRequirement(
            evaluation_model="llama3.3 70b",
            value=["Do not source PyEnvironment, pyenv, or run pyenv activate."],
            positive_examples=["pip install numpy"],
            negative_examples=["source ~/.pyenv/bin/activate"],
            token_limit=1024,
            name="No PyEnvironment"
        ),
        WrittenRequirement(
            evaluation_model="llama3.3 70b",
            value=["Do not run the final Python script or code written by the agent."],
            positive_examples=["echo 'Hello, World!'"],
            negative_examples=["python script.py"],
            token_limit=1024,
            name="No Run Python"
        )
    ])

# Define the SmartModel configuration
smart_model_config = ModelConfig(
    name="SmartModel",
    provider="groq",
    provider_model="llama-3.3-70b-versatile",
    api_key_env="GROQ_API_KEY",
    requirements=[
        SyntaxTreeValidatorRequirement(
            nodes=assistant_interaction_syntax,
            name="Assistant Interaction Syntax"
        )
    ]
)