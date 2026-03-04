"""
New code must not introduce TODO or FIXME comments.

TODOs left in committed code tend to stay forever. File a ticket instead.
This requirement is pertinent to any file type that has added lines.
"""

import re
from Alejandro.CodeRequirements.context import ProjectContext, PertinentResult, ValidateResult

name = "No new TODOs"
description = (
    "Diffs must not introduce TODO or FIXME comments. "
    "Track work in issues, not inline annotations."
)

_TODO = re.compile(r'#\s*(TODO|FIXME)\b', re.IGNORECASE)


def pertinent(context: ProjectContext) -> PertinentResult:
    files_with_additions = [d for d in context.diffs if d.added_lines]
    if not files_with_additions:
        return PertinentResult(
            is_pertinent=False,
            reason="No added lines in diff",
        )
    return PertinentResult(
        is_pertinent=True,
        reason=f"{len(files_with_additions)} file(s) have added lines",
    )


def validate(context: ProjectContext) -> ValidateResult:
    violations: list[str] = []
    for diff in context.diffs:
        for line in diff.added_lines:
            if _TODO.search(line):
                violations.append(f"  {diff.path}: {line.strip()}")
    if violations:
        return ValidateResult(
            passed=False,
            reason="TODO/FIXME comment(s) introduced:\n" + "\n".join(violations),
        )
    return ValidateResult(passed=True, reason="No new TODOs")
