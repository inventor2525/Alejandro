"""
Definition of the SmartModel for RequiredAI.
"""

from RequiredAI.ModelConfig import *
from RequiredAI.RequirementTypes import *
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

script_node = find_syntax_node(
	assistant_interaction_syntax,
	start_regex=r"^\s*<AI_RESPONSE>\s*$"
)

if bash_node:
	bash_node.requirements = [
		WrittenRequirement(
			evaluation_model="llama",
			value=["Do not include git push commands.", "Do not push code to remote repositories in ANY way."],
			positive_examples=['git commit -m "A commit"'],
			negative_examples=["git push origin main"],
			token_limit=1024,
			name="Never push code to a remote repository!"
		),
		WrittenRequirement(
			evaluation_model="llama",
			value=["Do not source PyEnvironment, pyenv, or run pyenv activate."],
			positive_examples=["pip install numpy"],
			negative_examples=["source ~/.pyenv/bin/activate"],
			token_limit=1024,
			name="No PyEnvironment"
		),
		WrittenRequirement(
			evaluation_model="llama",
			value=["Do not run python the application."],
			positive_examples=["echo 'Hello, World!'"],
			negative_examples=["python script.py"],
			token_limit=1024,
			name="Do not run any python file."
		),
		WrittenRequirement(
			evaluation_model="llama",
			value=["Do not call tree on any directory."],
			positive_examples=["echo 'Hello, World!'"],
			negative_examples=["tree", "ls"],
			token_limit=1024,
			name="Never call tree or ls."
		)
	]

if script_node:
	script_node.requirements = [
		WrittenRequirement(
			evaluation_model="llama",
			value=["If you need to mkdir, do it before saving any files."],
			positive_examples=["```txt\n<AI_RESPONSE>\n### AI_BASH_START ###\nmkdir -p /home/charlie/Projects/my_proj\n### AI_BASH_END ###\n### AI_SAVE_START: /home/charlie/Projects/my_proj/app.py ###\n# Do Stuff.\n### AI_SAVE_END ###\n### AI_BASH_START ###\ncd /home/charlie/Projects/my_proj\ngit init\n### AI_BASH_END ###<END_OF_INPUT>\n```"],
			negative_examples=["```txt\n<AI_RESPONSE>\n### AI_SAVE_START: /home/charlie/Projects/my_proj/app.py ###\n# Do Stuff.\n### AI_SAVE_END ###\n### AI_BASH_START ###\nmkdir -p /home/charlie/Projects/my_proj\ncd /home/charlie/Projects/my_proj\ngit init\n### AI_BASH_END ###<END_OF_INPUT>\n```"],
			token_limit=1024,
			name="Don't forget to do some things bash wise that might need to be done up front, before you save files."
		)
	]

llama_model_config = ModelConfig(
	name="llama",
	provider="groq",
	provider_model="qwen/qwen3-32b",#"llama-3.1-8b-instant",#"openai/gpt-oss-20b",#"llama-3.3-70b-versatile",
	api_key_env="GROQ_API_KEY"
)
# Define the SmartModel configuration
smart_model_config = ModelConfig(
	name="SmartModel",
	provider="RequiredAI",
	provider_model="llama",
	requirements=[
		ContainsRequirement(
			value=["```txt\n<AI_RESPONSE>"],
			name="Must have at least 1 ai script *in* a markdown text block."
		),
		SyntaxTreeValidatorRequirement(
			nodes=assistant_interaction_syntax,
			name="Assistant Interaction Syntax"
		)
	]
)