import unittest
import os
from RequiredAI.requirements import RequirementResult
from pathlib import Path
from typing import List

from Alejandro.Models.syntax_tree_requirement import (
    SyntaxTreeNode,
    SyntaxTreeValidatorRequirement,
)

class TestSyntaxTreeValidator(unittest.TestCase):
    """Tests for SyntaxTreeValidatorRequirement."""

    def setUp(self):
        """Set up the syntax tree validator and file paths."""
        self.test_dir = Path(__file__).parent/"syntax_tree_validator"
        self.good_file = self.test_dir / "good.txt"
        self.bad_file = self.test_dir / "bad.txt"

        # Define the assistant interaction syntax tree
        from Alejandro.Models.assistant_interaction_syntax import assistant_interaction_syntax
        self.syntax_tree = assistant_interaction_syntax

        self.validator = SyntaxTreeValidatorRequirement(
            nodes=self.syntax_tree,
            name="Assistant Interaction Syntax"
        )

    def _load_examples(self, file_path: Path) -> List[str]:
        """Load examples from a file, splitting on separator."""
        if not file_path.exists():
            self.fail(f"File {file_path} does not exist.")
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        # Split on separator with newlines
        examples = [ex for ex in content.split("\n==========\n")]
        return examples

    def test_good_examples(self):
        """Test that all examples in good.txt pass validation."""
        examples = self._load_examples(self.good_file)
        
        for i, example in enumerate(examples):
            with self.subTest(example=i):
                result: RequirementResult = self.validator.evaluate(
                    [{"role": "assistant", "content": example}]
                )
                self.assertTrue(
                    result.__bool__(),
                    f"Good example {i} failed: {result.evaluation_log.get('msg', None)}\nExample:\n{example}"
                )

    def test_bad_examples(self):
        """Test that all examples in bad.txt fail validation."""
        examples = self._load_examples(self.bad_file)
        
        for i, example in enumerate(examples):
            with self.subTest(example=i):
                result: RequirementResult = self.validator.evaluate(
                    [{"role": "assistant", "content": example}]
                )
                self.assertFalse(
                    result.__bool__(),
                    f"Bad example {i} passed unexpectedly: {result.evaluation_log.get('msg', None)}\nExample:\n{example}"
                )

if __name__ == "__main__":
    unittest.main()