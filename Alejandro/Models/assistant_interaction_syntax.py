from .syntax_tree_requirement import SyntaxTreeNode

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
						start_regex=r"^\s*### AI_SAVE_START:.*$",
						end_regex=r"^\s*### AI_SAVE_END.*$",
						validate_start_regex=r"^### AI_SAVE_START: /[^\s]+ ###$",
						validate_end_regex=r"^### AI_SAVE_END ###$",
						children=[
							SyntaxTreeNode(
								start_regex=r"^\s*### AI_READ_LINES:.*$",
								validate_start_regex=r"^\s*### AI_READ_LINES: /[^\s]+:\d+:\d+.* ###$"
							)
						]
					),
					SyntaxTreeNode(
						start_regex=r"^\s*### AI_BASH_START.*$",
						end_regex=r"^\s*### AI_BASH_END.*$",
						validate_start_regex=r"^### AI_BASH_START ###$",
						validate_end_regex=r"^### AI_BASH_END ###$",
					),
					SyntaxTreeNode(
						start_regex=r"^\s*### AI_READ_FILE.*$",
						validate_start_regex=r"^### AI_READ_FILE: /[^\s]* ###$"
					),
					SyntaxTreeNode(
						start_regex=r"^\s*### AI_APPLY_CHOICES.*$",
						end_regex=r"^\s*### AI_APPLY_CHOICES_END.*$",
						validate_start_regex=r"^### AI_APPLY_CHOICES: /[^\s]* ###$",
						validate_end_regex=r"^### AI_APPLY_CHOICES_END ###$",
					)
				]
			)
		]
	)
]