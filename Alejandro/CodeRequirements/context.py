from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class FileDiff:
    path: str
    '''Absolute path to the changed file.'''

    raw_diff: str
    '''Raw unified diff from get_git_diff (header lines stripped).'''

    annotated_diff: str
    '''Diff annotated with change numbers and interleaved file content with line
    numbers, from add_change_numbers(add_line_numbers=True). Use this in
    pertinent() to decide whether a requirement applies.'''

    hunks: list[dict]
    '''Hunk metadata: [{"number": "Change #1", "header": "@@...@@", "content": "..."}]'''

    added_lines: list[str]
    '''Lines added in this diff (leading + stripped). Use in validate().'''

    removed_lines: list[str]
    '''Lines removed in this diff (leading - stripped). Use in validate().'''


@dataclass
class ProjectContext:
    project_dir: str
    '''Root directory of the project being checked.'''

    diffs: list[FileDiff]
    '''One FileDiff per changed file.'''

    def files_matching(self, suffix: str) -> list[FileDiff]:
        """Return diffs for files whose path ends with suffix."""
        return [d for d in self.diffs if d.path.endswith(suffix)]

    def diff_for(self, path: str) -> FileDiff | None:
        """Return the diff for a specific absolute path, or None."""
        for d in self.diffs:
            if d.path == path:
                return d
        return None


@dataclass
class EvalResult:
    """
    Returned by both pertinent() and validate() on a requirement.

    For pertinent(): passed=True means the requirement applies to this diff.
    For validate():  passed=True means the code satisfies the requirement.
    """

    passed: bool
    '''The boolean result of this evaluation.'''

    reason: str = ""
    '''Human-readable explanation shown in audit output.'''

    model_context: Any = None
    '''Anything the requirement wants to carry back — model messages, LLM
    responses, intermediate results, etc. Not interpreted by the checker.'''

    error: str | None = None
    '''Set when the evaluation function raised or hit an unexpected state.'''


@dataclass
class RequirementResult:
    """Aggregated result for one requirement across both evaluation phases."""

    name: str
    '''Requirement name, from the loaded file.'''

    file_path: str
    '''Source file this requirement was loaded from.'''

    pertinent: EvalResult
    '''Result of calling requirement.pertinent(context).'''

    validate: EvalResult | None = None
    '''Result of calling requirement.validate(context).
    None when pertinent.passed was False.'''
