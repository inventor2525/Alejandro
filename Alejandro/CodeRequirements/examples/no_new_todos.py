"""
New code must not introduce TODO or FIXME comments.

TODOs left in committed code tend to stay there permanently.
Track work in issues instead. Pertinent to any file type that has added lines.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, EvalResult

name = "No new TODOs"
description = "Diffs must not introduce TODO or FIXME comments. Track work in issues."

_TODO = re.compile(r'#\s*(TODO|FIXME)\b', re.IGNORECASE)


def pertinent(context: ProjectContext) -> EvalResult:
    files_with_additions = [d for d in context.diffs if d.added_lines]
    if not files_with_additions:
        return EvalResult(passed=False, reason="No added lines in diff")
    return EvalResult(passed=True, reason=f"{len(files_with_additions)} file(s) with added lines")


def validate(context: ProjectContext) -> EvalResult:
    violations: list[str] = []
    for diff in context.diffs:
        for line in diff.added_lines:
            if _TODO.search(line):
                violations.append(f"  {diff.path}: {line.strip()}")
    if violations:
        return EvalResult(
            passed=False,
            reason="TODO/FIXME comment(s) introduced:\n" + "\n".join(violations),
        )
    return EvalResult(passed=True, reason="No new TODOs")
