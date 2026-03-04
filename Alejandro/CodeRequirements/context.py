"""
Data classes that flow through the code requirements system.

ProjectContext  — built once per check run; passed to every requirement's
                  pertinent() and validate() functions.

FileDiff        — one changed file's diff, parsed into added/removed lines
                  with the full new file content attached when readable.

PertinentResult — returned by requirement.pertinent():
                  tells the checker whether this requirement applies to the
                  current diff, with optional model context or error info.

ValidateResult  — returned by requirement.validate():
                  the actual pass/fail decision, same rich return structure.

RequirementResult — aggregates one requirement's pertinent + validate results;
                    validate is None when the requirement was not pertinent.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileDiff:
    path: str
    diff_text: str
    added_lines: list[str]
    removed_lines: list[str]
    new_content: str | None = None


@dataclass
class ProjectContext:
    project_dir: str
    diffs: list[FileDiff]

    @property
    def changed_files(self) -> list[str]:
        return [d.path for d in self.diffs]

    def diff_for(self, path: str) -> FileDiff | None:
        for d in self.diffs:
            if d.path == path:
                return d
        return None

    def diffs_matching(self, suffix: str) -> list[FileDiff]:
        return [d for d in self.diffs if d.path.endswith(suffix)]


@dataclass
class PertinentResult:
    """
    Whether a requirement applies to the current diff.

    is_pertinent  — False means the checker skips validate() entirely.
    reason        — human-readable explanation (shown in audit output).
    model_context — anything the requirement wants to preserve: model messages,
                    intermediate results, raw LLM response, etc.
    error         — set if pertinent() itself raised or hit an unexpected state.
    """
    is_pertinent: bool
    reason: str = ""
    model_context: Any = None
    error: str | None = None


@dataclass
class ValidateResult:
    """
    Whether the code change satisfies the requirement.

    passed        — the bottom-line pass/fail.
    reason        — human-readable explanation of why it passed or failed.
    model_context — same as PertinentResult.model_context: carry anything useful.
    error         — set if validate() itself raised.
    """
    passed: bool
    reason: str = ""
    model_context: Any = None
    error: str | None = None


@dataclass
class RequirementResult:
    """Aggregated result for one requirement across both evaluation phases."""
    name: str
    file_path: str
    pertinent: PertinentResult
    validate: ValidateResult | None = None   # None ↔ requirement was not pertinent
