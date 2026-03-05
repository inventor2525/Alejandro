from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path

from assistant_merger.git_tools import get_git_diff, add_change_numbers

from .context import ProjectContext, FileDiff, EvalResult, RequirementResult
from .loader import CodeRequirement


@dataclass
class CheckResult:
    """
    The outcome of running a full set of requirements against a diff. Returned
    by check() and intended to be surfaced directly in whatever pipeline or UI
    consumes it — a gate, a report, a conversation message, etc. The results
    list contains one entry per requirement regardless of pertinency, so nothing
    is silently dropped and the full audit trail is always available.
    """

    all_passed: bool
    '''True when every pertinent requirement's validate passed.'''

    results: list[RequirementResult]
    '''Full audit trail — one entry per requirement regardless of pertinency.'''

    @property
    def pertinent(self) -> list[RequirementResult]:
        """
        Subset of results where pertinent.passed is True.

        Returns:
            RequirementResults that applied to this diff.
        """
        return [r for r in self.results if r.pertinent.passed]

    @property
    def failed(self) -> list[RequirementResult]:
        """
        Pertinent requirements whose validate did not pass.

        Returns:
            RequirementResults that applied and whose validate returned passed=False.
        """
        return [r for r in self.pertinent if r.validate and not r.validate.passed]


def check(
    requirements: list[CodeRequirement],
    project_dir: str,
    diffs: list[FileDiff] | None = None,
) -> CheckResult:
    """
    Run all requirements against the project's current uncommitted diff.

    For each requirement, calls pertinent(context) first. If that returns
    passed=False the requirement is recorded as non-pertinent and validate is
    skipped. If passed=True, validate(context) is called and its result
    recorded. Exceptions from either function are caught and stored as
    EvalResult(passed=False, error=...) so one broken requirement never
    aborts the rest.

    Args:
        requirements: Requirements to evaluate, typically from load_requirements().
        project_dir:  Root of the git repository being checked.
        diffs:        Pre-built diff list. If None, generated from project_dir
                      via git diff HEAD (with --cached as fallback).

    Returns:
        CheckResult with all_passed and the full per-requirement audit trail.
    """
    if diffs is None:
        diffs = _get_diffs(project_dir)

    context = ProjectContext(project_dir=project_dir, diffs=diffs)
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
    """
    Build a FileDiff list from the current git state of project_dir.

    Tries git diff HEAD first; falls back to --cached for staged-only
    repositories. Each changed file is annotated via assistant_merger so
    requirement authors get change numbers and interleaved line numbers
    without having to implement that themselves.

    Args:
        project_dir: Root of the git repository to diff.

    Returns:
        One FileDiff per changed file, skipping files with no readable diff.
    """
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
