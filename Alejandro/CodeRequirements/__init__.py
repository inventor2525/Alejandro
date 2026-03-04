"""
Code requirements loader and checker.

Usage
─────
    from Alejandro.CodeRequirements import load_requirements, check

    reqs = load_requirements(directory="/path/to/my_requirements")
    reqs += load_requirements(directory="~/.alejandro/requirements")

    result = check(reqs, project_dir="/path/to/project")

    if not result.all_passed:
        for r in result.failed:
            print(r.name, r.validate.reason)

Requirement files
─────────────────
Each .py file in a requirements directory must define:

    name: str
    description: str

    def pertinent(context: ProjectContext) -> PertinentResult: ...
    def validate(context: ProjectContext) -> ValidateResult: ...

Files starting with '_' are skipped by the directory loader.
"""

from __future__ import annotations

import importlib.util
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .context import (
    ProjectContext, FileDiff,
    PertinentResult, ValidateResult, RequirementResult,
)


@dataclass
class CodeRequirement:
    name: str
    description: str
    file_path: str
    pertinent: Callable[[ProjectContext], PertinentResult]
    validate: Callable[[ProjectContext], ValidateResult]


@dataclass
class CheckResult:
    all_passed: bool
    results: list[RequirementResult]

    @property
    def pertinent(self) -> list[RequirementResult]:
        return [r for r in self.results if r.pertinent.is_pertinent]

    @property
    def failed(self) -> list[RequirementResult]:
        return [r for r in self.pertinent if r.validate and not r.validate.passed]


# ── Loading ───────────────────────────────────────────────────────────────────

def load_requirements(
    directory: str | None = None,
    pattern: str = "*.py",
    paths: list[str] | None = None,
) -> list[CodeRequirement]:
    """
    Load CodeRequirement objects from a directory glob and/or explicit file paths.

    Results from both sources are combined in order (directory first, then paths),
    so the returned list can be extended with further load_requirements() calls:

        reqs = load_requirements(directory="./project_reqs")
        reqs += load_requirements(directory="~/.alejandro/reqs")
    """
    found: list[str] = []

    if directory:
        base = Path(directory).expanduser()
        for p in sorted(base.glob(pattern)):
            if not p.name.startswith('_'):
                found.append(str(p))

    if paths:
        found.extend(paths)

    return [_load_file(p) for p in found]


def _load_file(path: str) -> CodeRequirement:
    spec = importlib.util.spec_from_file_location("_code_req", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return CodeRequirement(
        name=getattr(mod, 'name', Path(path).stem),
        description=getattr(mod, 'description', ''),
        file_path=path,
        pertinent=mod.pertinent,
        validate=mod.validate,
    )


# ── Diff parsing ──────────────────────────────────────────────────────────────

def _get_diffs(project_dir: str) -> list[FileDiff]:
    result = subprocess.run(
        ['git', 'diff', 'HEAD'],
        capture_output=True, text=True, cwd=project_dir
    )
    if result.returncode != 0 or not result.stdout.strip():
        # Fall back to staged-only diff (nothing committed yet)
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            capture_output=True, text=True, cwd=project_dir
        )
    return _parse_diff(result.stdout, project_dir)


def _parse_diff(diff_text: str, project_dir: str) -> list[FileDiff]:
    diffs: list[FileDiff] = []
    path: str | None = None
    lines: list[str] = []
    added: list[str] = []
    removed: list[str] = []

    def flush() -> None:
        if path is None:
            return
        d = FileDiff(
            path=path,
            diff_text='\n'.join(lines),
            added_lines=added[:],
            removed_lines=removed[:],
        )
        try:
            d.new_content = Path(path).read_text()
        except Exception:
            pass
        diffs.append(d)

    for line in diff_text.splitlines():
        if line.startswith('diff --git '):
            flush()
            path = None
            lines = [line]
            added = []
            removed = []
        elif line.startswith('+++ b/'):
            path = str(Path(project_dir) / line[6:])
            lines.append(line)
        elif line.startswith('+') and not line.startswith('+++'):
            lines.append(line)
            added.append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            lines.append(line)
            removed.append(line[1:])
        else:
            lines.append(line)

    flush()
    return diffs


# ── Checker ───────────────────────────────────────────────────────────────────

def check(
    requirements: list[CodeRequirement],
    project_dir: str,
    diffs: list[FileDiff] | None = None,
) -> CheckResult:
    """
    Run all requirements against the project's current diff.

    Algorithm per requirement:
      1. Call pertinent(context)  — if not pertinent, validate stays None
      2. Call validate(context)   — only when pertinent
      3. Wrap both in RequirementResult and collect

    diffs can be provided explicitly (e.g. from a prior git diff call);
    if omitted they are generated from the project directory via git.

    Returns CheckResult with all_passed=True only when every pertinent
    requirement's validate result passed.
    """
    if diffs is None:
        diffs = _get_diffs(project_dir)

    context = ProjectContext(project_dir=project_dir, diffs=diffs)
    results: list[RequirementResult] = []

    for req in requirements:
        try:
            pertinent_result = req.pertinent(context)
        except Exception as e:
            pertinent_result = PertinentResult(
                is_pertinent=False,
                error=f"pertinent() raised: {e}",
            )

        validate_result: ValidateResult | None = None
        if pertinent_result.is_pertinent:
            try:
                validate_result = req.validate(context)
            except Exception as e:
                validate_result = ValidateResult(
                    passed=False,
                    error=f"validate() raised: {e}",
                )

        results.append(RequirementResult(
            name=req.name,
            file_path=req.file_path,
            pertinent=pertinent_result,
            validate=validate_result,
        ))

    all_passed = all(
        r.validate.passed
        for r in results
        if r.pertinent.is_pertinent and r.validate is not None
    )

    return CheckResult(all_passed=all_passed, results=results)
