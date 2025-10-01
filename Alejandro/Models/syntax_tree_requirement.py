from RequiredAI.helpers import json_dataclass, field
from dataclasses_json import config
from typing import List, Optional, Set, Dict
import re
from RequiredAI.Requirement import Requirements
from RequiredAI.RequirementTypes import requirement, Requirement, RequirementResult
import uuid

@json_dataclass
class SyntaxTreeNode:
	"""A node in a syntax tree with regex-based start and end conditions."""
	
	start_regex: str
	end_regex: Optional[str] = None
	validate_start_regex: Optional[str] = None
	validate_end_regex: Optional[str] = None
	requirements: List[Requirement] = field(default=None, metadata=config(
			decoder=Requirements.from_dict, encoder=Requirements.to_dict
		)
	) # This handles the polymorphism of Requirement
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
@json_dataclass
class SyntaxTreeValidatorRequirement(Requirement):
	"""Requirement that enforces a syntax tree structure on the response."""
	
	nodes: List[SyntaxTreeNode]
	name: str = ""
	_prompt_info: str = field(default="", init=False)
	
	def __post_init__(self):
		"""Populate _other_nodes_catch_regexes for each node."""
		self._all_nodes:Dict[str, SyntaxTreeNode] = {}
		
		open_list = list(self.nodes)
		while len(open_list)>0:
			node = open_list.pop()
			if not hasattr(node, "__uuid__"):
				node.__uuid__ = str(uuid.uuid4())
			
			if node.__uuid__ not in self._all_nodes:
				self._all_nodes[node.__uuid__] = node
				open_list.extend(node.children)
		
		for node_uuid, node in self._all_nodes.items():
			node.__child_uuids__ = set([child.__uuid__ for child in node.children])
			
		# For each node, find catch regexes of non-self, non-direct-child nodes
		for node_uuid, node in self._all_nodes.items():
			node._other_nodes_catch_regexes = set()
			for other_node_uuid, other_node in self._all_nodes.items():
				if other_node_uuid == node_uuid or other_node_uuid in node.__child_uuids__:
					continue
				node._other_nodes_catch_regexes.add(other_node.start_regex)
				if other_node.end_regex:
					node._other_nodes_catch_regexes.add(other_node.end_regex)
	
	def evaluate(self, messages: List[Dict[str,str]]) -> RequirementResult:
		"""
		Evaluates if the response follows the syntax tree structure and node requirements.
		
		Args:
			messages: List of message dictionaries
			
		Returns:
			RequirementResult: True if the syntax tree and requirements are followed, False otherwise
		"""
		self._prompt_info = ""
		
		last_message = messages[-1]
		content = last_message.get("content", "")
		
		lines = content.splitlines()
		current_nodes = self.nodes
		node_stack = []
		line_index = 0
		
		while line_index < len(lines):
			line = lines[line_index]
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
						return RequirementResult.construct(self, False, {
							"msg":self._prompt_info
						})
					
					# Check for invalid catch regexes from other nodes
					for catch_regex in node._other_nodes_catch_regexes:
						if re.search(catch_regex, line):
							self._prompt_info = (
								f"Line {line_index + 1}: '{line}' contains invalid marker matching "
								f"regex '{catch_regex}' from another node."
							)
							return RequirementResult.construct(self, False, {
								"msg":self._prompt_info
							})
					
					# Evaluate requirements for single-line nodes (no end_regex)
					if not node.end_regex:
						if node.requirements:
							for req in node.requirements:
								if not req.evaluate([{"role": "assistant", "content": line}]):
									self._prompt_info = (
										f"Node with start regex '{node.start_regex}' failed requirement "
										f"'{req.__class__.__requirement_type__}' on content:\n{line[:100]}..."
									)
									return RequirementResult.construct(self, False, {"msg": self._prompt_info})
						line_index += 1
						found_match = True
						break
					
					# Enter content-collecting node
					node_stack.append((node, current_nodes, []))
					current_nodes = node.children
					found_match = True
					line_index += 1
					break
			
			for _, __, nodes_content in node_stack[:-1]:
				nodes_content.append(line)
			
			if found_match:
				continue
			
			# Check for end of current node (only for nodes with end_regex)
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
						return RequirementResult.construct(self, False, {
							"msg":self._prompt_info
						})
					
					# Evaluate requirements for this node
					if current_node.requirements:
						node_content = "\n".join(node_stack[-1][2])
						for req in current_node.requirements:
							req:Requirement
							# Pass content as a single message
							if not req.evaluate([{"role": "assistant", "content": node_content}]):
								self._prompt_info = (
									f"Syntax node with start regex '{current_node.start_regex}' and end regex '{current_node.end_regex}' failed requirement "
									f"{req.__class__.__requirement_type__} requirement '{req.name}' on content:\n{node_content[:100]}..."
								)
								return RequirementResult.construct(self, False, {
									"msg":self._prompt_info
								})
					
					# Pop back to parent node
					node, parent_nodes, parent_content = node_stack.pop()
					current_nodes = parent_nodes
					current_content = parent_content
					found_match = True
					line_index += 1
					continue
				else:
					node_stack[-1][2].append(line)
			
			# Check for invalid catch regexes from other nodes (only if in a content-collecting node)
			if node_stack:
				current_node = node_stack[-1][0]
				for catch_regex in current_node._other_nodes_catch_regexes:
					if re.search(catch_regex, line):
						self._prompt_info = (
							f"Line {line_index + 1}: '{line}' contains invalid marker matching "
							f"regex '{catch_regex}' from another node while in node with "
							f"start regex '{current_node.start_regex}'."
						)
						return RequirementResult.construct(self, False, {
							"msg":self._prompt_info
						})
			
			line_index += 1
		
		# Check if we're back at the root (all content-collecting nodes closed)
		if node_stack:
			current_node = node_stack[-1][0]
			self._prompt_info = (
				f"Incomplete syntax: reached end of content while in node with "
				f"start regex '{current_node.start_regex}', expecting end regex "
				f"'{current_node.end_regex}'."
			)
			return RequirementResult.construct(self, False, {
				"msg":self._prompt_info
			})
			
		return RequirementResult.construct(self, True, {
			"msg":self._prompt_info
		})
	
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
	
	print(assistant_interaction_requirement.evaluate([{"content":r"""

```txt
<AI_RESPONSE>
<END_OF_INPUT>
```

"""}]).__bool__())