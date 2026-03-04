from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path

from assistant_merger.git_tools import get_git_diff, add_change_numbers

from .context import ProjectContext, FileDiff, EvalResult, RequirementResult
from .loader import CodeRequirement


@dataclass
class CheckResult:
    """Result of running a list of requirements against a project diff."""

    all_passed: bool
    '''True when every pertinent requirement's validate passed.'''

    results: list[RequirementResult]
    '''Full audit trail — one entry per requirement regardless of pertinency.'''

    @property
    def pertinent(self) -> list[RequirementResult]:
        """Requirements that were pertinent to the current diff."""
        return [r for r in self.results if r.pertinent.passed]

    @property
    def failed(self) -> list[RequirementResult]:
        """Pertinent requirements whose validate did not pass."""
        return [r for r in self.pertinent if r.validate and not r.validate.passed]


def check(
    requirements: list[CodeRequirement],
    project_dir: str,
    diffs: list[FileDiff] | None = None,
    conversation: list[dict] | None = None,
    client=None,
) -> CheckResult:
    """
    Run all requirements against the project's current uncommitted diff.

    For each requirement:
      1. Call pertinent(context) — if passed=False, validate is skipped (stays None)
      2. Call validate(context)  — only when pertinent returned passed=True

    diffs may be provided explicitly; if omitted they are generated from
    project_dir using assistant_merger.git_tools (git diff HEAD, or --cached
    fallback). Context is built once before the loop.

    conversation and client are passed through to ProjectContext so that
    model-evaluated requirements (e.g. no_unsolicited_try_except) can query
    an LLM about the conversation history.
    """
    if diffs is None:
        diffs = _get_diffs(project_dir)

    context = ProjectContext(
        project_dir=project_dir,
        diffs=diffs,
        conversation=conversation or [],
        client=client,
    )
    results: list[RequirementResult] = []

    for req in requirements:
        try:
            pertinent_result = req.pertinent(context)
        except Exception as e:
            pertinent_result = EvalResult(passed=False, error=f"pertinent() raised: {e}")

        validate_result: EvalResult | None = None
        if pertinent_result.passed:
            try:
                validate_result = req.validate(context)
            except Exception as e:
                validate_result = EvalResult(passed=False, error=f"validate() raised: {e}")

        results.append(RequirementResult(
            name=req.name,
            file_path=req.file_path,
            pertinent=pertinent_result,
            validate=validate_result,
        ))

    all_passed = all(
        r.validate.passed
        for r in results
        if r.pertinent.passed and r.validate is not None
    )

    return CheckResult(all_passed=all_passed, results=results)


def _get_diffs(project_dir: str) -> list[FileDiff]:
    for args in (
        ['git', 'diff', '--name-only', 'HEAD'],
        ['git', 'diff', '--cached', '--name-only'],
    ):
        result = subprocess.run(args, capture_output=True, text=True, cwd=project_dir)
        if result.returncode == 0 and result.stdout.strip():
            break

    changed = [
        str(Path(project_dir) / f)
        for f in result.stdout.strip().splitlines()
        if f.strip()
    ]

    diffs: list[FileDiff] = []
    for abs_path in changed:
        p = Path(abs_path)
        raw_diff, err = get_git_diff(p)
        if err or not raw_diff:
            continue
        annotated, hunks = add_change_numbers(raw_diff, p, add_line_numbers=True)
        added = [l[1:] for l in raw_diff.splitlines() if l.startswith('+') and not l.startswith('+++')]
        removed = [l[1:] for l in raw_diff.splitlines() if l.startswith('-') and not l.startswith('---')]
        diffs.append(FileDiff(
            path=abs_path,
            raw_diff=raw_diff,
            annotated_diff=annotated,
            hunks=hunks,
            added_lines=added,
            removed_lines=removed,
        ))

    return diffs
