from __future__ import annotations
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .context import ProjectContext, EvalResult


@dataclass
class CodeRequirement:
    """
    An enforceable rule about any aspect of a codebase, loaded from a Python
    file that defines pertinent() and validate(). Rules can cover anything
    with a diff-observable answer: documentation coverage, tool usage, naming
    conventions, process constraints, structural limits — not just style or
    quality in the narrow sense. The two-phase design (pertinent then validate)
    keeps expensive checks from running on diffs they don't apply to.
    """

    name: str
    '''Display name of the requirement.'''

    description: str
    '''What this requirement enforces.'''

    file_path: str
    '''Absolute path to the source file this requirement was loaded from.'''

    pertinent: Callable[[ProjectContext], EvalResult]
    '''Returns EvalResult(passed=True) if this requirement applies to the diff.
    Returning passed=False skips validate entirely.'''

    validate: Callable[[ProjectContext], EvalResult]
    '''Returns EvalResult(passed=True) if the diff satisfies this requirement.
    Only called when pertinent returned passed=True.'''


def load_requirements(
    directory: str | None = None,
    pattern: str = "*.py",
    paths: list[str] | None = None,
) -> list[CodeRequirement]:
    """
    Load CodeRequirement objects from a directory glob and/or explicit file paths.

    Files starting with '_' are skipped by the directory loader. Returns a
    plain list so callers can compose from multiple sources:

        reqs = load_requirements(directory="./project/.requirements")
        reqs += load_requirements(directory="~/.alejandro/requirements")

    Args:
        directory: Directory to glob for requirement files. Skipped if None.
        pattern:   Glob pattern applied inside directory. Defaults to "*.py".
        paths:     Explicit list of file paths to load in addition to the glob.

    Returns:
        List of CodeRequirement objects in glob-sorted order, with any explicit
        paths appended after.
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
    """
    Import a requirement file by path and construct a CodeRequirement from it.

    Args:
        path: Absolute or relative path to the requirement Python file.

    Returns:
        CodeRequirement populated from the module's name, description,
        pertinent, and validate attributes.
    """
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
