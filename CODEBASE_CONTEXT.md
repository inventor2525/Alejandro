# Codebase Context — Alejandro + Related Frameworks
*Reference document for Claude sessions. Update this when you learn something new.*
*Last updated: 2026-03-02*

> **Note:** A summary of the RequiredAI framework was produced in a separate branch of the RequiredAI repo during a prior session. If you need deep detail on RequiredAI internals beyond what is in the "Framework Deep Dives" section below, check that branch first before re-researching from source.

---

## Directory Map

```
/home/user/
  Alejandro/                    ← main project (this repo)
    Alejandro/
      Core/                     ← word stream, controls, application loop, assistant
      Models/                   ← data models + RequiredAI syntax integration
      web/                      ← Flask app, blueprints, SSE events, terminal
    examples/
      smart_model.py            ← SmartModel config (THIS IS THE KEY INTEGRATION FILE)
      run_server.py             ← starts RequiredAI server for Alejandro
      run_client.py             ← test client
    tests/
    CLAUDE_SESSION_GUIDE.md     ← branch management, WLK race condition fix
    dear_claude.md              ← WhisperLiveKit source + API reference
    CODEBASE_CONTEXT.md         ← THIS FILE
    ARCHITECTURE.md             ← vision + architecture for the full system (replaces STRUCTURED_REVIEW_GOAL.md)

  assistant_interaction/        ← LLM→filesystem command execution layer
    assistant_interaction/utils.py   ← process_commands(), the whole parser
    README.md                        ← LLM-facing instructions + format spec
    app.py                           ← Flask UI (port 5002) for copy-paste workflow

  assistant_merger/             ← diff engine used by assistant_interaction
    assistant_merger/git_tools.py    ← get_git_diff, add_change_numbers, apply_changes

  RequiredAI/                   ← requirement-validated LLM completions
    RequiredAI/
      Requirement.py            ← base Requirement, RequirementResult, @requirement decorator
      RequirementTypes.py       ← ContainsRequirement, RegexRequirement, WrittenRequirement
      ModelConfig.py            ← ModelConfig, InheritedModel, FallbackModel, InputConfig
      ModelManager.py           ← singleton, provider instantiation
      system.py                 ← RequiredAISystem, the convergence loop
      server.py                 ← Flask server (port 5432 in Alejandro's usage)
      client.py                 ← HTTP client (create_completion, get_status, stop)
      providers/                ← anthropic, groq, gemini, requiredai, fallback
      json_dataclass/           ← @json_dataclass decorator, UUID id tracking
    examples/server_config.json ← server startup config (models + fallbacks)
```

---

## System Architecture

### Full Data Flow (voice → filesystem)

```
Microphone
    ↓ WebSocket audio bytes
WhisperLiveKitWordStream  (Core/WhisperLiveKitWordStream.py)
    ↓ yields WordNode objects (word, start_time, end_time, linked list)
Application.run()  (Core/Application.py)
    ↓ matches words against Screen's Control keyphrases
Control.action() / ModalControl  (Core/Control.py, Core/ModalControl.py)
    ↓ dispatches (or pushes SSE event to browser if js_getter_function set)
Screen subclass method  (web/blueprints/*.py, etc.)
    ↓ may call
Assistant.send_message()  (Core/Assistant.py)
    ↓ HTTP POST to RequiredAI server (localhost:5432)
RequiredAISystem.chat_completions()  (RequiredAI/system.py)
    ↓ convergence loop (draft → evaluate requirements → revise → repeat)
LLM response (guaranteed to meet all WrittenRequirements)
    ↓ content is an assistant_interaction AI script
    ↓ (returned to browser, or pasted into assistant_interaction Flask UI)
assistant_interaction.utils.process_commands()
    ↓ parses <AI_RESPONSE>...<END_OF_INPUT>
    ↓ runs bash / saves files / reads files / applies diff choices
assistant_merger.git_tools  (diff generation + hunk apply/revert)
    ↓
Diff or file contents returned to LLM context
```

---

## Framework Deep Dives

### 1. assistant_interaction

**What it does:** Parses an LLM response in a special scripting format and executes commands on the filesystem.

**Entry point:** `process_commands(input_text: str) -> str`

**Parsing:** Simple stateful line-by-line parser. No real AST — just flag variables (`in_bash`, `in_save`, etc.). The syntax is validated separately by `SyntaxTreeValidatorRequirement` in `smart_model.py`.

**Markers (execution order matters):**
| Marker | Effect | Returns |
|--------|--------|---------|
| `### AI_BASH_START ###` / `### AI_BASH_END ###` | `subprocess.run(shell=True)` | stdout + stderr |
| `### AI_SAVE_START: /abs/path ###` / `### AI_SAVE_END ###` | writes file | numbered diff (via assistant_merger) or read_file if untracked |
| `### AI_READ_LINES: /path:start:end ###` | inline embed during save | (spliced into save content) |
| `### AI_READ_FILE: /path ###` | reads file with line numbers | `--- File: ... ---\n{numbered content}` |
| `### AI_APPLY_CHOICES: /path ###` / `### AI_APPLY_CHOICES_END ###` | accept/reject diff hunks | new numbered diff of result |

**Rules the LLM must follow (from README.md):**
- Never push code
- Don't merge and save in the same round
- Don't use AI_READ_LINES on a file you just saved (line numbers are stale)
- AI script must be the last thing in the response
- Always use absolute paths
- Don't run scripts in background
- Never explain what you did unless asked
- Always include type hints + docstrings

---

### 2. assistant_merger

**What it does:** Produces LLM-navigable numbered diffs and applies accept/reject decisions.

**`get_git_diff(file_path)`** → `(diff_str, error)`
- Uses `git diff --unified=0` (no context lines, only changed lines)
- Strips the first 4 header lines (keeps only hunks)

**`add_change_numbers(diff, file_path, add_line_numbers=False)`** → `(annotated_diff, hunks_list)`
- Numbers each hunk: `@@ -10,3 +10,4 @@ (Change #1)`
- Appends an `@@ End Change #N Hunk @@` sentinel
- After each hunk, inserts actual file lines from that point to the next hunk (spatial context)
- Optionally adds line numbers to context lines
- Returns `hunks` list: `[{number, header, content}, ...]`

**`apply_changes(file_path, diff, llm_response)`** → `merged_file_str`
- Parses `Change #N, Yes/No` or `Change #N, <Merge_Replace_Hunk>...</Merge_Replace_Hunk>`
- Processes hunks in reverse order (avoids line number drift)
- `Yes` = keep new content (no-op, it's already in the file)
- `No` = revert hunk to pre-change content (extracted from diff `-` lines)
- `<Merge_Replace_Hunk>` = replace hunk with custom literal content

**Important:** The diff is always from last commit → current working file, not from prior change. The LLM works on uncommitted changes, and the user decides when to commit.

---

### 3. RequiredAI

**What it does:** Wraps any LLM call in an iterative quality gate. A response is only returned when all requirements pass.

**Core loop (`system.py:RequiredAISystem.chat_completions`):**
```python
prospect = model.complete(messages)
while True:
    for req in requirements:
        result = req.evaluate(messages + [prospect])
        if not result:
            revision_prompt = revise_template.format(req.prompt)
            prospect = (req.revision_model or model).complete(
                messages + [prospect, revision_prompt]
            )
            break  # restart from first requirement
    else:
        break  # all passed
return prospect
```
Key design choice: restart from scratch on any failure (don't carry failure history into revision — "not leading the witness").

**Requirement types:**
- `ContainsRequirement(value: List[str])` — substring check, free/instant
- `RegexRequirement(positive_regexes, negative_regexes)` — regex match/no-match
- `WrittenRequirement(evaluation_model, value, positive_examples, negative_examples)` — uses a second LLM to semantically evaluate; expensive but flexible
- `SyntaxTreeValidatorRequirement(nodes)` — validates hierarchical marker structure (used for assistant_interaction scripts)

**Key classes:**
- `ModelConfig(name, provider, provider_model, requirements, input_config)` — defines a model with requirements
- `InheritedModel(name, base_model, requirements, input_config)` — creates a ModelConfig with `provider='RequiredAI'` that pipes through base_model + adds requirements
- `FallbackModel` — tries multiple models, returns first non-error response that meets requirements
- `InputConfig(messages_to_include, filter_roles, filter_tags)` — controls what slice of the conversation a given model sees

**`@requirement(name)`** decorator — registers a class in the `_REQUIREMENT_REGISTRY`, enabling JSON serialization/deserialization.

**`@json_dataclass`** — RequiredAI's own dataclass decorator that adds `.to_json()`, `.from_json()`, `.to_dict()`, `.from_dict()`, and optional UUID id tracking.

---

### 4. Alejandro/Models/

**`assistant_interaction_syntax.py`** — defines the expected structure of an LLM assistant_interaction response as a tree of `SyntaxTreeNode` objects with regex-based start/end/validate patterns. Used by `smart_model.py`.

**`syntax_tree_requirement.py`** — implements `SyntaxTreeValidatorRequirement`, a `@requirement("SyntaxTreeValidator")` that walks a response line-by-line matching it against the syntax tree. Reports the exact line and reason for failure. Each node can also carry its own `requirements` list that gets evaluated against that node's content (e.g. the bash block node in `smart_model.py` has WrittenRequirements: no git push, no pyenv, no python run, no tree/ls).

**`Conversation.py`** — `Message` and `Conversation` `@json_dataclass` models. Conversations persist to `~/Documents/Alejandro/Conversations/{uuid}.json`. Messages support parent/children (tree structure), tags, model_name, extra dict.

---

### 5. examples/smart_model.py — The Integration Centrepiece

This is the most important file for understanding how everything connects. It defines `SmartModel` — the RequiredAI model that wraps the LLM used for code work.

**Model hierarchy:**
```
SmartModel (RequiredAI provider → "llama")
  requirements:
    - ContainsRequirement: response must have ```txt\n<AI_RESPONSE>
    - SyntaxTreeValidatorRequirement: must follow assistant_interaction syntax tree
      ↓ which has per-node requirements:
      bash node:
        - Written: no git push
        - Written: no pyenv sourcing
        - Written: no running python files
        - Written: no tree/ls calls
      script root node:
        - Written: mkdir before saving files

llama (groq → openai/gpt-oss-120b)
  - the actual drafting model
```

**The `browse` model** shows a selective context pattern: `input_config=InputConfig(messages_to_include=[(0,-1), ""], filter_tags=['browse'])` — only sees messages tagged 'browse'. Demonstrates how different modes/screens can have tailored model views.

**The `talk` model** (`Assistant.py`) has WrittenRequirements via InheritedModel:
- No Apologies (eval: gpt-oss-20b)
- No over explaining (eval: gpt-oss-120b)
- No kiss up (eval: gpt-oss-120b)
- No explaining codeblock contents (eval: gpt-oss-20b, revision: gemini-pro)

---

## Key Patterns to Understand

### Pattern 1: Requirement as a convergence constraint
A `Requirement` is not a filter — it's a quality gate with a self-description of why it failed (`prompt` property). This description is fed back to the model as a revision request. The model re-drafts until all requirements pass. Requirements are composable and can be evaluated by different models.

### Pattern 2: SyntaxTree + per-node requirements = structural + semantic validation
`SyntaxTreeValidatorRequirement` + per-node `requirements` = a response that is both syntactically well-formed AND semantically sound within each structural block. The bash node's WrittenRequirements are evaluated only against the bash block's content, not the whole response.

### Pattern 3: InheritedModel = base model + requirement wrapper
`InheritedModel("Name", base_model, requirements=[...])` produces a `ModelConfig` with `provider='RequiredAI'` and `provider_model=base_model.name`. RequiredAI then routes it back through itself with the base model doing actual completion and RequiredAI enforcing the requirements. Clean composition.

### Pattern 4: The LLM sees the diff, not just the output
After `save_file`, the LLM gets back `add_change_numbers(diff)` output with numbered hunks and file context. The LLM is expected to review these and respond with `AI_APPLY_CHOICES`. This is the current human-in-the-loop code review mechanism.

### Pattern 5: Human is loop-closer, not loop-runner
The human doesn't run code or evaluate diffs themselves in normal flow. They copy output back to the LLM. The new structured review system wants to automate this loop while keeping the human in authoritative control of requirements.

---

## Important File Locations (Runtime)

| What | Path |
|------|------|
| Conversations | `~/Documents/Alejandro/Conversations/*.json` |
| RequiredAI server | `localhost:5432` |
| assistant_interaction Flask UI | `localhost:5002` |
| Global user requirements (proposed) | `~/Documents/requirements/` ← TBD |
| Project requirements | `<project>/.requirements/` ← TBD |

---

## Gotchas and Sharp Edges

1. **Line numbers stale after save/merge** — `AI_READ_LINES` uses live file line numbers. After any `AI_SAVE` or `AI_APPLY_CHOICES`, those numbers are wrong. The LLM must re-read the file or use diff line numbers.

2. **Diffs are always commit→working**, not delta-to-delta. The LLM works on uncommitted state. All intermediate diffs are from the last commit.

3. **No save+merge in same round** — merging requires the current diff, saving overwrites the file (creating a new diff). You can't get the diff you need to merge if you've already saved over it.

4. **`apply_changes` uses hunks in reverse** — must process highest line numbers first or earlier reverts shift line positions for later ones.

5. **`WrittenRequirement` is stochastic** — it picks one random phrasing from `value` list and a random subset of examples. Consecutive evaluations of the same content may give different results. By design — enables probabilistic consensus.

6. **RequiredAI convergence loop is theoretically infinite** — it only stops when all requirements pass or client calls stop. A badly-specified requirement (impossible to satisfy) loops forever.

7. **`SyntaxTreeNode._other_nodes_catch_regexes`** — automatically computed: any marker from a sibling/cousin node that appears inside this node is a validation error. Prevents e.g. `### AI_BASH_START ###` appearing inside a `### AI_SAVE_START ###` block.

8. **Branch permissions** — Claude Code web sessions can only push to branches ending in their session ID (see CLAUDE_SESSION_GUIDE.md).

9. **pyenv** — cannot be sourced from within bash blocks on the laptop. Instruct user to run things themselves when pyenv is needed.

10. **`Conversation.save()`** makes a directory on import** — `os.makedirs(Conversation.ROOT_DIRECTORY, exist_ok=True)` runs at module load time.
