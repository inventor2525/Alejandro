# Structured Code Review System — Goal Specification
*Living document. Human edits are authoritative. AI may propose additions in marked sections.*
*Status: DRAFT — iterate with user before implementing*

---

## Vision (User Story)

As a developer working with an LLM assistant, I want every code change produced by the LLM to be automatically validated against a set of coding requirements — structural, stylistic, and semantic — so that I never have to manually catch things like missing docstrings, single-use helper functions, over-engineered solutions, or changes that weren't part of the request. The system should be traceable, auditable, and composable. Humans author requirements. AI produces code that must satisfy them. The requirements ARE the specification.

---

## Core Principles

1. **Human artifacts are word of god.** Requirements authored by humans cannot be modified by AI. They can only be read, evaluated against, and iterated toward. They are the permanent record of intent.

2. **Everything must be traceable.** Every requirement has an author, an author type (human vs ai-proposed), and a creation date. Every diff review has a log. Every acceptance or rejection has a reason. Conversation history that led to a requirement's creation is stored alongside it.

3. **Code can be rebuilt from requirements alone.** The set of human-authored requirements, combined with the README and architecture artifacts, should be sufficient to reconstruct the project from scratch.

4. **AI time is cheap. Human time is not.** Latency is the bottleneck on AI side. Correctness and clarity are the bottlenecks on human side. Design should minimize human touches per change while maximizing human authority over what "correct" means.

5. **Requirements are code.** A requirement is a Python file with a `validate()` function, a `pertinent()` function, and a machine-parsable header. They are tested, committed, and treated as first-class project artifacts.

---

## CodeRequirement File Format

Every requirement is a `.py` file. The block comment header is machine-parsable.

```python
"""
requirement_name: No single-use helper functions
author: charlie
author_type: human
created: 2025-01-15
description: >
  As a developer, I want the LLM to avoid creating helper functions
  that are only called from one place, because that adds indirection
  without abstraction value. The logic should live inline unless
  it is reused or the function name itself carries meaningful
  documentation value.
"""
from typing import Tuple


def pertinent(file_path: str, diff: str) -> bool:
	"""
	Returns True if this requirement is applicable to the given change.
	Use this to scope requirements (e.g. only .py files, only files
	that contain threading, only files in a specific module, etc.)
	"""
	return file_path.endswith('.py')


def validate(file_path: str, diff: str) -> Tuple[bool, str]:
	"""
	Returns (passed, explanation).
	explanation is shown to the LLM as the revision prompt when passed=False.

	Receives the current file path and the unified diff of the change.
	May also read the full file at file_path for deeper analysis.
	"""
	# ... implementation
	return True, ""
```

**Rules:**
- `author_type: human` — file is locked. AI cannot modify it.
- `author_type: ai-proposed` — file lives in `proposed/` subdir. Humans review and promote.
- `pertinent()` must be fast and cheap (no LLM calls).
- `validate()` may call an LLM (e.g. via RequiredAI WrittenRequirement) or use static analysis.
- The file is loaded via `eval()` / `importlib`, not imported as a module — keeps them isolated and hot-reloadable.

---

## Requirement Storage Layout

```
~/Documents/requirements/           ← global, user-level requirements
  no_apologies.req.py              ← LLM behavior (maps to existing WrittenRequirements)
  always_use_tabs.req.py
  camel_case.req.py
  big_docstrings.req.py
  proposed/
    ai_proposed_xyz.req.py         ← AI may only write here

<project>/.requirements/           ← project-level requirements, tracked by git
  no_single_use_helpers.req.py
  no_duplicate_code.req.py
  no_overcomplicated_changes.req.py
  docstrings_required.req.py
  no_unnecessary_try_catch.req.py
  no_unrelated_changes.req.py      ← THIS IS THE MOST IMPORTANT ONE
  proposed/
    ai_proposed_xyz.req.py

<project>/.requirements/history/   ← TBD: conversation logs that led to requirement creation
  no_single_use_helpers/
    conversation_2025-01-15.json   ← the Alejandro conversation where this was decided
```

---

## Structured Review Process Flow

This extends the existing `assistant_interaction` workflow. The LLM still writes AI scripts. What changes is what happens to the diffs those scripts produce.

### Current Flow (baseline)
```
1. LLM writes AI script (SmartModel: syntax + bash requirements enforced)
2. User runs script
3. Diff returned to LLM
4. LLM decides Accept/Reject per hunk via AI_APPLY_CHOICES
5. Repeat 1-4 until good
6. User says "commit"
7. LLM commits
8. (Push: user explicitly requests)
```

### New Flow (goal)
```
1. LLM writes AI script (SmartModel: unchanged, still enforces syntax + bash rules)
2. Script executed → diffs produced
3. [NEW] Per-file diff analysis:
   a. Load applicable CodeRequirements (pertinent() == True for this file/diff)
   b. For each requirement, run validate(file_path, diff)
   c. Flag hunks that fail requirements (with reason)
   d. Flag hunks that appear unrelated to the stated task (via WrittenRequirement)
4. [NEW] Auto-generate a partial AI_APPLY_CHOICES rejecting all flagged hunks
   (user can override before submitting)
5. [NEW] LLM re-reviews the diff WITH requirement failure annotations
   → Produces revised AI_APPLY_CHOICES (must satisfy all requirements to be accepted)
6. [NEW] After merge, run requirements against the final file state (not just the diff)
7. [NEW] Only after all requirements pass: mark as "ready for commit"
8. [NEW] User controls: tag current state, mark as checkpoint, attach note
9. Push only explicitly requested by user AND only after review process complete
```

---

## Requirement Categories

These are the initial coding requirement types to implement:

### Structural / Style
- `docstrings_required` — all new functions/methods/classes have docstrings
- `type_hints_required` — all new function signatures have type annotations
- `always_use_tabs` — indentation uses tabs, not spaces
- `camel_case_functions` — function names use camelCase (or snake_case — pick one, be consistent per project)
- `no_magic_numbers` — literal numeric values should be named constants

### Code Quality
- `no_single_use_helpers` — no helper functions called from exactly one place (unless the name itself is meaningful documentation)
- `no_duplicate_code` — same logic block should not appear more than once
- `no_over_engineered_change` — change should not add abstraction layers, configuration points, or generalization that wasn't asked for
- `no_unnecessary_try_catch` — try/except blocks should only exist at system boundaries (user input, external APIs), not around internal code that can't fail
- `no_excessive_conditions` — no deeply nested if/elif chains where a lookup table or early return would serve

### Change Scope
- `no_unrelated_changes` — **the most important one**: given the stated task, every hunk in the diff should be directly necessary for that task. Reformats, comment additions, variable renames not asked for, surrounding code cleanup — all are violations.
- `no_removed_prior_code` — do not remove previously-existing code unless specifically requested (covers accidentally dropping functions, imports, etc.)
- `task_completeness` — the change should actually accomplish what was asked (positive check)

### LLM Behavior (maps to existing WrittenRequirements, but now as .req.py files)
- `no_apologies`
- `no_over_explaining`
- `no_kiss_up`
- `no_code_explanation` (in coding context)

---

## Integration with Existing Architecture

### How CodeRequirements map onto RequiredAI

A `CodeRequirement.validate()` is logically equivalent to a `Requirement.evaluate()`. The difference:
- RequiredAI requirements evaluate LLM *responses* (text)
- CodeRequirements evaluate *code diffs* (file + diff string)

They should share the same convergence loop logic. A `CodeRequirement` should be wrappable as a RequiredAI `Requirement` subclass, so the same revision/retry machinery applies.

```python
# Proposed: CodeRequirementAsRequirement adapter
class CodeRequirementAsRequirement(Requirement):
    """Wraps a CodeRequirement for use in RequiredAI's convergence loop."""
    code_req_path: str  # path to the .req.py file
    file_path: str
    diff: str

    def evaluate(self, messages) -> RequirementResult:
        req = load_code_requirement(self.code_req_path)
        passed, explanation = req.validate(self.file_path, self.diff)
        return RequirementResult.construct(self, passed, {"explanation": explanation})

    @property
    def prompt(self):
        req = load_code_requirement(self.code_req_path)
        return req.__doc__  # the user story from the module docstring
```

### Where in the pipeline

The review step hooks in at the `save_file()` return point in `assistant_interaction/utils.py`. Currently `save_file` returns the diff. The new system intercepts that diff, runs requirements, and returns an annotated diff with flagged hunks.

The LLM's subsequent `AI_APPLY_CHOICES` response is then validated: it must reject all requirement-failing hunks (or provide a replacement via `<Merge_Replace_Hunk>`).

### SyntaxTreeNode requirements (existing) vs CodeRequirements (new)

The existing `SyntaxTreeNode.requirements` on the bash node check the bash block *before execution*. The new CodeRequirements check the *resulting diff* after execution. They are complementary:
- Pre-execution: syntax + behavioral constraints on what the LLM writes
- Post-execution: code quality constraints on what actually changed

---

## User Controls

### Tagging Current State
The user should be able to mark a specific commit/state with a label and note. This becomes a reference point:
- "This is the last known good state"
- "This is the version I demo'd"
- "Requirements were satisfied here"

Implementation: a git tag with a structured message. Could be done via a voice control in Alejandro ("tag this", "mark checkpoint") or via a web UI control.

### Requirement Override
The user should be able to:
- Suppress a specific requirement for a specific change (with a required reason)
- Promote an AI-proposed requirement to human-authored
- Archive/disable a requirement without deleting it (it stays in history)

### Review Dashboard (Web UI)
A screen in Alejandro's web interface showing:
- Current pending change
- Per-hunk requirement status (pass/fail/suppressed)
- Audit trail of current review cycle
- One-click approve/reject controls

---

## Traceability System

Every artifact in this system has provenance:

| Artifact | Author | Stored | Immutable? |
|----------|--------|--------|-----------|
| CodeRequirement (`author_type: human`) | Human | `.requirements/*.req.py` (git) | Yes — AI cannot modify |
| CodeRequirement (`author_type: ai-proposed`) | AI | `.requirements/proposed/*.req.py` | Until promoted by human |
| Review log | System | `.requirements/review_log/*.json` | Yes |
| Conversation history | Session | `~/Documents/Alejandro/Conversations/*.json` | Yes (append-only) |
| Requirement creation conversation | Human-tagged | `.requirements/history/<req_name>/` | Yes |
| Commit | System | git | Yes (after user approval) |

**Invariant:** An audit trail must exist for every committed change. The trail includes: which requirements were checked, which passed/failed, what revisions were attempted, and the final LLM response that was accepted.

---

## Open Questions / Clarifications Needed

*(Items to resolve with user before implementing)*

1. **Where does `no_unrelated_changes` get the "stated task"?** The requirement needs to know what was asked. Does it come from the current conversation context? A `# Task:` comment the LLM must include in its script? A separate task-description message tagged specially?

2. **How are CodeRequirements loaded?** `eval()` on the file string? `importlib.util.spec_from_file_location`? The latter is safer. What's the sandbox model for `validate()`—can it make network calls? LLM calls?

3. **Global vs project requirements precedence.** If a global requirement conflicts with a project requirement, which wins? Or are they always additive (both must pass)?

4. **What does "AI cannot modify human requirements" mean mechanically?** Read-only filesystem permissions? A hash in the file header verified on load? A git hook that rejects changes to non-`proposed/` files by AI commits? Or just by convention enforced at the application level?

5. **`pertinent()` for bash blocks.** CodeRequirements currently scope to file_path + diff. But bash scripts don't have a file_path. Does `pertinent()` get a second argument `block_type: str` ('save', 'bash', 'file')? Or are bash-block requirements handled separately (they already live in `SyntaxTreeNode.requirements`)?

6. **Review UI integration.** Is the review dashboard a new Alejandro Screen? Or does it live in the `assistant_interaction` Flask app? Or both (one for voice-driven, one for copy-paste workflow)?

7. **How does the LLM learn which requirement failed?** Currently `requirement.prompt` is a string fed back as a revision prompt. For code requirements, is the revision prompt just the requirement's docstring + the specific hunk that failed? Or a full re-drafting request?

8. **Requirement testing.** Requirements are `.py` files. They should have tests. Where do those tests live? In `<project>/tests/requirements/`? Or alongside the requirement file?

9. **Conversation history attachment.** When a requirement is promoted from ai-proposed to human, is the user prompted to attach the conversation that led to that decision? How is the linkage stored?

10. **Naming convention: `.req.py` or something else?** The `.req.py` extension signals to tooling that these files are requirements, not application code. Any reason to prefer a different convention (e.g., `requirements/docstrings_required.py`, or a YAML/TOML header instead of a Python docstring)?

---

## What Is NOT In Scope

- Replacing the existing `assistant_interaction` scripting format — extend it, don't replace it
- Replacing `RequiredAI` — build on top of it
- Automated test running (that's a separate concern; requirements are about code quality gates, not correctness tests)
- AI-driven architectural decisions — requirements define what "good code" looks like; the AI implements code that satisfies them, it does not define what "good" means
- Any change to how `Conversation.py` or the web session layer works (unless the review dashboard requires it)

---

## Implementation Sketch (Not Yet Approved)

*Do not implement until design is finalized with user.*

### Phase 1: CodeRequirement Infrastructure
- `CodeRequirement` base loader (importlib, isolated, header parsing)
- `.requirements/` directory convention + git-tracked
- `pertinent()` + `validate()` interface
- Tests for the loader itself

### Phase 2: Diff Review Hook
- Hook into `assistant_interaction/utils.py:save_file()` return path
- Load applicable requirements, run validate() on each hunk or full diff
- Annotate the diff output with `[FAIL: requirement_name] explanation` markers
- Return annotated diff to LLM

### Phase 3: RequiredAI Integration
- `CodeRequirementAsRequirement` adapter class
- Wrap the review step in a RequiredAI convergence loop
- LLM's `AI_APPLY_CHOICES` validated: must address all failing hunks

### Phase 4: User Controls
- Tagging / checkpoint voice command in Alejandro
- Web UI review screen (new Screen subclass)
- Requirement promotion workflow (ai-proposed → human)

### Phase 5: Traceability
- Review log persistence
- Conversation history linkage to requirements
- Global `~/Documents/requirements/` loading
