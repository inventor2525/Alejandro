from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileDiff:
    """
    All diff data for a single changed file, pre-parsed into the forms most
    useful to requirement authors. Passed inside ProjectContext to every
    pertinent() and validate() call.
    """

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
    """
    Everything a requirement needs to evaluate a proposed change. Built once
    per check() call and passed to every pertinent() and validate() call in
    that run. Requirement files should not import application modules to obtain
    this data — it is injected here so requirements stay decoupled from the
    application that runs them.
    """

    project_dir: str
    '''Root directory of the project being checked.'''

    diffs: list[FileDiff]
    '''One FileDiff per changed file.'''

    conversation: list[dict] = field(default_factory=list)
    '''Full conversation history in RequiredAI message format (role/content dicts).
    Pass this to model requirements that need to reason about what the user asked for.'''

    client: Any = None
    '''RequiredAI client. Passed through so requirement files can call models directly
    without importing from a specific application module.'''

    def files_matching(self, suffix: str) -> list[FileDiff]:
        """
        Return diffs for files whose path ends with suffix.

        Args:
            suffix: File extension or path suffix to filter by (e.g. '.py').

        Returns:
            Subset of self.diffs whose path ends with suffix.
        """
        return [d for d in self.diffs if d.path.endswith(suffix)]

    def diff_for(self, path: str) -> FileDiff | None:
        """
        Return the diff for a specific absolute path.

        Args:
            path: Absolute path to look up.

        Returns:
            The matching FileDiff, or None if the file is not in the diff set.
        """
        for d in self.diffs:
            if d.path == path:
                return d
        return None


@dataclass
class EvalResult:
    """
    The outcome of a single evaluation step — either a pertinent() or
    validate() call. The same type is used for both so that CheckResult and
    RequirementResult can hold them uniformly without branching on phase.
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
    """
    The full outcome of running one requirement against a diff — both the
    pertinent decision and, when pertinent passed, the validate decision.
    Collected into CheckResult.results to form the complete audit trail for
    a check() call.
    """

    name: str
    '''Requirement name, from the loaded file.'''

    file_path: str
    '''Source file this requirement was loaded from.'''

    pertinent: EvalResult
    '''Result of calling requirement.pertinent(context).'''

    validate: EvalResult | None = None
    '''Result of calling requirement.validate(context).
    None when pertinent.passed was False.'''
