"""
No raw print() calls in production Python code.

Use a logger instead. print() is fine in scripts and __main__ blocks but
should not appear in library or application source.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, PertinentResult, ValidateResult

name = "No print statements"
description = (
    "Python source files should not introduce raw print() calls. "
    "Use a logger or push_event instead."
)

_PRINT = re.compile(r'\bprint\s*\(')


def pertinent(context: ProjectContext) -> PertinentResult:
    py_with_additions = [
        d for d in context.diffs_matching('.py') if d.added_lines
    ]
    if not py_with_additions:
        return PertinentResult(
            is_pertinent=False,
            reason="No Python files with added lines in diff",
        )
    return PertinentResult(
        is_pertinent=True,
        reason=f"{len(py_with_additions)} Python file(s) have added lines",
    )


def validate(context: ProjectContext) -> ValidateResult:
    violations: list[str] = []
    for diff in context.diffs_matching('.py'):
        for line in diff.added_lines:
            if _PRINT.search(line):
                violations.append(f"  {diff.path}: {line.strip()}")
    if violations:
        return ValidateResult(
            passed=False,
            reason="print() call(s) introduced:\n" + "\n".join(violations),
        )
    return ValidateResult(passed=True, reason="No new print() calls")
