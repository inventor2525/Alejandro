"""
except clauses must name a specific exception type.

Bare `except:` swallows KeyboardInterrupt and SystemExit.
At minimum use `except Exception:`. Pertinent whenever any Python file
has added lines in the diff.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, EvalResult

name = "No bare excepts"
description = "except clauses must name a specific exception type, never bare `except:`."

_BARE_EXCEPT = re.compile(r'^\s*except\s*:\s*$')


def pertinent(context: ProjectContext) -> EvalResult:
    """
    Check whether any Python files have added lines.

    Args:
        context: Project context containing diffs of changed files.

    Returns:
        EvalResult(passed=True) if any Python files have added lines.
    """
    py_diffs = [d for d in context.files_matching('.py') if d.added_lines]
    if not py_diffs:
        return EvalResult(passed=False, reason="No Python files with added lines")
    return EvalResult(passed=True, reason=f"{len(py_diffs)} Python file(s) with additions")


def validate(context: ProjectContext) -> EvalResult:
    """
    Check added lines for bare except clauses.

    Args:
        context: Project context containing diffs of changed files.

    Returns:
        EvalResult(passed=True) if no bare except clauses were introduced.
    """
    violations: list[str] = []
    for diff in context.files_matching('.py'):
        for line in diff.added_lines:
            if _BARE_EXCEPT.match(line):
                violations.append(f"  {diff.path}: {line.rstrip()}")
    if violations:
        return EvalResult(
            passed=False,
            reason="Bare except clause(s) introduced:\n" + "\n".join(violations),
        )
    return EvalResult(passed=True, reason="No bare excepts")
