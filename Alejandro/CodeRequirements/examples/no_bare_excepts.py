"""
Bare except clauses must not be introduced.

`except:` swallows everything including KeyboardInterrupt and SystemExit.
Always name at least one exception type: `except Exception:` at minimum.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, PertinentResult, ValidateResult

name = "No bare excepts"
description = "except clauses must name a specific exception type, never bare `except:`."

_BARE_EXCEPT = re.compile(r'^\s*except\s*:\s*$')


def pertinent(context: ProjectContext) -> PertinentResult:
    py_diffs = [d for d in context.diffs_matching('.py') if d.added_lines]
    if not py_diffs:
        return PertinentResult(
            is_pertinent=False,
            reason="No Python files with added lines in diff",
        )
    return PertinentResult(
        is_pertinent=True,
        reason=f"{len(py_diffs)} Python file(s) have added lines",
    )


def validate(context: ProjectContext) -> ValidateResult:
    violations: list[str] = []
    for diff in context.diffs_matching('.py'):
        for line in diff.added_lines:
            if _BARE_EXCEPT.match(line):
                violations.append(f"  {diff.path}: {line.rstrip()}")
    if violations:
        return ValidateResult(
            passed=False,
            reason="Bare except clause(s) introduced:\n" + "\n".join(violations),
        )
    return ValidateResult(passed=True, reason="No bare excepts")
