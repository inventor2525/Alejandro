"""
Python source files should not introduce raw print() calls.
Use a logger or push_event instead. print() is fine in scripts and
__main__ blocks but should not appear in library or application source.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, EvalResult

name = "No print statements"
description = "Python source files must not introduce raw print() calls."

_PRINT = re.compile(r'\bprint\s*\(')


def pertinent(context: ProjectContext) -> EvalResult:
    py_diffs = [d for d in context.files_matching('.py') if d.added_lines]
    if not py_diffs:
        return EvalResult(passed=False, reason="No Python files with added lines")
    return EvalResult(passed=True, reason=f"{len(py_diffs)} Python file(s) with additions")


def validate(context: ProjectContext) -> EvalResult:
    violations: list[str] = []
    for diff in context.files_matching('.py'):
        for line in diff.added_lines:
            if _PRINT.search(line):
                violations.append(f"  {diff.path}: {line.strip()}")
    if violations:
        return EvalResult(
            passed=False,
            reason="print() call(s) introduced:\n" + "\n".join(violations),
        )
    return EvalResult(passed=True, reason="No new print() calls")
