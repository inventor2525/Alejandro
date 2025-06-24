from dataclasses import dataclass, field
from typing import List, Optional, Set
import re
from requireai.requirements import requirement, Requirement

@dataclass
class SyntaxTreeNode:
    """A node in a syntax tree with regex-based start and end conditions."""
    
    start_regex: str
    end_regex: Optional[str] = None
    validate_start_regex: Optional[str] = None
    validate_end_regex: Optional[str] = None
    requirements: List[Requirement] = field(default_factory=list)
    children: List["SyntaxTreeNode"] = field(default_factory=list)
    _other_nodes_catch_regexes: Set[str] = field(default_factory=set, init=False)
    
    def __post_init__(self):
        """Validate regexes and compile them."""
        try:
            re.compile(self.start_regex)
            if self.end_regex:
                re.compile(self.end_regex)
            if self.validate_start_regex:
                re.compile(self.validate_start_regex)
            if self.validate_end_regex:
                re.compile(self.validate_end_regex)
        except re.error as e:
            raise ValueError(f"Invalid regex in node: {e}")

@requirement("SyntaxTreeValidator")
@dataclass
class SyntaxTreeValidatorRequirement(Requirement):
    """Requirement that enforces a syntax tree structure on the response."""
    
    nodes: List[SyntaxTreeNode]
    name: str = ""
    _prompt_info: str = field(default="", init=False)
    
    def __post_init__(self):
        """Populate _other_nodes_catch_regexes for each node."""
        all_nodes = set()
        
        def collect_nodes(node: SyntaxTreeNode):
            all_nodes.add(node)
            for child in node.children:
                collect_nodes(child)
        
        # Collect all nodes
        for node in self.nodes:
            collect_nodes(node)
        
        # For each node, find catch regexes of non-self, non-direct-child nodes
        for node in all_nodes:
            node._other_nodes_catch_regexes = set()
            for other_node in all_nodes:
                if other_node == node or other_node in node.children:
                    continue
                node._other_nodes_catch_regexes.add(other_node.start_regex)
                if other_node.end_regex:
                    node._other_nodes_catch_regexes.add(other_node.end_regex)
    
    def evaluate(self, messages: List[dict]) -> bool:
        """
        Evaluates if the response follows the syntax tree structure and node requirements.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            bool: True if the syntax tree and requirements are followed, False otherwise
        """
        self._prompt_info = ""
        if not messages:
            self._prompt_info = "No messages provided."
            return False
            
        last_message = messages[-1]
        content = last_message.get("content", "")
        
        if not isinstance(content, str):
            self._prompt_info = "Last message content is not a string."
            return False
            
        lines = content.splitlines()
        current_nodes = self.nodes
        node_stack = []
        line_index = 0
        current_content: List[str] = []
        
        while line_index < len(lines):
            line = lines[line_index].rstrip()
            found_match = False
            
            # Check for start of any current node
            for node in current_nodes:
                if re.match(node.start_regex, line):
                    # Validate start condition
                    validate_regex = node.validate_start_regex or node.start_regex
                    if not re.match(validate_regex, line):
                        self._prompt_info = (
                            f"Line {line_index + 1}: '{line}' matches start regex '{node.start_regex}' "
                            f"but fails validation regex '{validate_regex}'."
                        )
                        return False
                    
                    # Check for invalid catch regexes from other nodes
                    for catch_regex in node._other_nodes_catch_regexes:
                        if re.search(catch_regex, line):
                            self._prompt_info = (
                                f"Line {line_index + 1}: '{line}' contains invalid marker matching "
                                f"regex '{catch_regex}' from another node."
                            )
                            return False
                    
                    # Enter this node
                    node_stack.append((node, current_nodes, current_content))
                    current_nodes = node.children
                    current_content = []
                    found_match = True
                    line_index += 1
                    break
            
            if found_match:
                continue
            
            # Check for end of current node
            if node_stack and node_stack[-1][0].end_regex:
                current_node = node_stack[-1][0]
                if re.match(current_node.end_regex, line):
                    # Validate end condition
                    validate_regex = current_node.validate_end_regex or current_node.end_regex
                    if not re.match(validate_regex, line):
                        self._prompt_info = (
                            f"Line {line_index + 1}: '{line}' matches end regex '{current_node.end_regex}' "
                            f"but fails validation regex '{validate_regex}'."
                        )
                        return False
                    
                    # Evaluate requirements for this node
                    if current_node.requirements:
                        node_content = "\n".join(node_stack[-1][2])
                        for req in current_node.requirements:
                            # Pass content as a single message
                            if not req.evaluate([{"role": "assistant", "content": node_content}]):
                                self._prompt_info = (
                                    f"Node with start regex '{current_node.start_regex}' failed requirement "
                                    f"'{req.__class__.__web_name__}' on content:\n{node_content[:100]}..."
                                )
                                return False
                    
                    # Pop back to parent node
                    node, parent_nodes, parent_content = node_stack.pop()
                    current_nodes = parent_nodes
                    current_content = parent_content
                    found_match = True
                    line_index += 1
                    continue
            
            # Check for invalid catch regexes from other nodes
            if node_stack:
                current_node = node_stack[-1][0]
                for catch_regex in current_node._other_nodes_catch_regexes:
                    if re.search(catch_regex, line):
                        self._prompt_info = (
                            f"Line {line_index + 1}: '{line}' contains invalid marker matching "
                            f"regex '{catch_regex}' from another node while in node with "
                            f"start regex '{current_node.start_regex}'."
                        )
                        return False
                current_content.append(line)
            
            line_index += 1
        
        # Check if we're back at the root (all nodes closed)
        if node_stack:
            current_node = node_stack[-1][0]
            self._prompt_info = (
                f"Incomplete syntax: reached end of content while in node with "
                f"start regex '{current_node.start_regex}', expecting end regex "
                f"'{current_node.end_regex}'."
            )
            return False
            
        return True
    
    @property
    def prompt(self) -> str:
        """
        Returns a string explaining the syntax tree requirements and any failure details.
        """
        base_prompt = "Your response must follow the specified syntax tree structure, with correct start and end markers for each node and no invalid markers from other nodes."
        if self._prompt_info:
            return f"{base_prompt} Failure details: {self._prompt_info}"
        return base_prompt

if __name__ == "__main__":
    # Example: Assistant Interaction syntax tree
    assistant_interaction_syntax = [
        SyntaxTreeNode(
            start_regex=r"^\s*```txt\s*$",
            end_regex=r"^\s*```\s*$",
            validate_start_regex=r"^```txt$",
            validate_end_regex=r"^```$",
            children=[
                SyntaxTreeNode(
                    start_regex=r"^\s*<AI_RESPONSE>\s*$",
                    end_regex=r"^\s*<END_OF_INPUT>\s*$",
                    validate_start_regex=r"^<AI_RESPONSE>$",
                    validate_end_regex=r"^<END_OF_INPUT>$",
                    children=[
                        SyntaxTreeNode(
                            start_regex=r"^### AI_SAVE_START:.*$",
                            end_regex=r"^### AI_SAVE_END$",
                            validate_start_regex=r"^### AI_SAVE_START:\s*/[^\s]+.*$",
                            children=[
                                SyntaxTreeNode(
                                    start_regex=r"^\s*### AI_READ_LINES:.*$",
                                    validate_start_regex=r"^\s*### AI_READ_LINES:\s*/[^\s]+.*:\d+:\d+(?::\"[+-][^\"]*\")?$"
                                )
                            ]
                        ),
                        SyntaxTreeNode(
                            start_regex=r"^### AI_BASH_START$",
                            end_regex=r"^### AI_BASH_END$"
                        ),
                        SyntaxTreeNode(
                            start_regex=r"^### AI_READ_FILE:.*$",
                            validate_start_regex=r"^### AI_READ_FILE:\s*/[^\s]+.*$"
                        ),
                        SyntaxTreeNode(
                            start_regex=r"^### AI_APPLY_CHOICES:.*$",
                            end_regex=r"^### AI_APPLY_CHOICES_END$",
                            validate_start_regex=r"^### AI_APPLY_CHOICES:\s*/[^\s]+.*$"
                        )
                    ]
                )
            ]
        )
    ]
    
    # Create requirement instance
    assistant_interaction_requirement = SyntaxTreeValidatorRequirement(
        nodes=assistant_interaction_syntax,
        name="Assistant Interaction Syntax"
    )
    
    print("Assistant Interaction syntax tree defined:")
    print(assistant_interaction_requirement)