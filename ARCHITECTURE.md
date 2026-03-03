# Architecture — Alejandro / Required AI
*Living document. Human edits are authoritative. AI may propose additions but may not modify human-authored sections.*
*Status: EVOLVING — iterate with user before implementing specifics*

---

## What This System Is

Alejandro is not just a voice-controlled assistant. It is an attempt to build an AI that can extend itself — where the entire program (not just the LLM weights) is the intelligence. The LLM APIs are one component. The requirements built on top of them, the pipelines that orchestrate them, and the traceability infrastructure that records everything are equally part of the AI.

The central design challenge: human time is the scarcest resource. A human speaks slowly, reads slowly, and can only hold so much in working memory at once. AI is infinitely parallelizable. You can always add more compute. You cannot add more hours to a human's day. Every design decision flows from this asymmetry.

---

## Core Principles

1. **Human artifacts are the ground truth.** Requirements, user stories, and descriptions authored by humans cannot be modified by AI. They are the permanent record of intent. The AI builds toward them, never over them.

2. **Human time is the bottleneck, not AI compute.** AI is infinitely parallelizable. The constraint is how fast a human can speak, read, and decide. If something is mistranscribed or misunderstood, the cost falls entirely on the human who must re-say it. When intent is unclear, the AI should spend tokens re-reviewing and re-asking itself — not the human. Run a jury of 10 agents. Only escalate to the human when those agents genuinely disagree.

3. **When intent is ambiguous, run a jury — don't ask the human yet.** Spawn multiple agents and compare their interpretations. If all 10 agree, run with it. If they diverge, that's a genuine question worth raising. The human should only be interrupted when no amount of AI review resolves the ambiguity.

4. **Everything is a stream, and every stream is traceable.** Audio, transcription, tool calls, application events, key presses, pen strokes — all are streams. Everything is timestamped and recorded. Any session can be replayed from any point, with corrections applied forward from the correction point. A mistranscription is fixable because the audio still exists.

5. **LLMs are Q&A machines, not architects.** They excel at answering one focused question with constrained context. They are poor at building an airplane. This is not a limitation that scale will fully remove — an LLM that could build an airplane couldn't build a city. The way to build a city is to decompose it into 10,000 individual Q&A problems, chain the answers together, and build a process that can decompose more problems. Every design decision should trace back to this realization.

6. **Requirements are code.** A requirement is a Python file with a `validate()` function and a `pertinent()` function. They are executable, committed to git, versioned, and auditable. They are not configuration or documentation — they are first-class program artifacts.

7. **Models are nestable.** A "model" in this system is not a raw LLM. It is an LLM (or another model) combined with requirements and an input configuration. Models compose: outer models add requirements without the inner model knowing. Any model exposes a standard OpenAI-compatible interface.

8. **Human requirements are verbatim.** When a human creates a requirement by speaking, their exact words go into the description field. The AI never paraphrases intent into a requirement unless the human reviews and approves. The audio reference is always included so it can be replayed, re-transcribed, or annotated later.

---

## Terminology

To avoid confusion about the word "model":

| Term | Meaning |
|------|---------|
| **LLM** | Raw weights from a provider (Anthropic, OpenAI, Groq, etc.) |
| **Model** (in this system) | LLM (or another Model) + requirements + InputConfig; exposed as an OpenAI-compatible endpoint; usable as the base for another Model |

When this document says "model" without qualification, it means the composition — not just the weights.

---

## Everything Is a Stream

While it may not yet be implemented this way: The system is best understood as a set of parallel streams, all timestamped and recorded:

| Stream | Contents |
|--------|----------|
| Audio stream | Raw audio bytes from microphone or playback |
| Word stream | Timestamped transcribed words (linked list of WordNodes) |
| Command/event stream | Tool calls, AI script commands, control triggers, navigation events |
| Pen/touch stream | Screen touch events, pen strokes (future) |
| Conversation stream | Messages exchanged with LLM models |

These streams run in parallel and all reference the same timeline. An audio timestamp in a requirement file links back to the word stream which links back to the audio stream. If the transcription was wrong, the audio is still there. A better transcription model applied later can correct it.

Ideally in the future: Any development session can be replayed entirely — the file tree rebuilt from scratch by replaying the command stream. If you want to correct a decision made after a mistranscription or misinterpretation, you could correct it, or have an agent correct it with human annotation as input, and then replay forward from that point.

---

## Author Model

Every artifact has a specific author. Not "human" vs "AI" — a named author with identity and context.

Examples:
- `author: Charlie Mehlenbeck`
- `author: Claude-claude-sonnet-4-6`
- `author: Claude-claude-opus-4-6 (proposed, pending review)`

When a human creates a requirement by speaking, their verbatim words (as transcribed) go directly into the requirement's description field. The audio timestamp range is also recorded so the original audio can be retrieved — both for traceability and because a better transcription model might later be available. If the user explicitly instructs the AI to write a requirement on their behalf, their words are still copied verbatim and attributed to them. The AI never paraphrases a human's stated intent into a requirement unless the human reviews and approves that paraphrase.

AI-authored artifacts are never falsely attributed to a human author. The validation pipeline enforces this — a model tasked with placing requirements checks that any requirement it creates carries its own authorship, not a human's name, unless it was explicitly told to create on that human's behalf.

Models that are even capable of modifying or adding requirements enforce such things with requirements that are a part of those models.

---

## The Model Concept

"Model" in this codebase means more than an LLM. A model is:

```
Model = LLM (or another Model) + Requirements + InputConfig
```

**Requirements** constrain what the model can output. The convergence loop retries until all requirements pass.

**InputConfig** controls what slice of the conversation the model sees:
- Python-style slice of message history: `messages[-10:]`, `messages[0:1]`
- Tag filtering: only messages tagged `browse`, only messages tagged `code`
- Hard-coded context strings: inject static content (like example requirements) without it existing as a conversation message
- Most-recent filtering: keep only the most recent application event of a given tag

**Nestability**: A model can be built on top of another model. The outer model adds requirements without the inner model knowing. The inner model's output is the candidate; the outer model's requirements gate it.

**Nestability example:**

```
MedicalTalkModel
  base: TalkModel
  requirements: [OnlyMedicalContent, NeverWriteCode]

TalkModel
  base: anthropic/claude-sonnet-4-6
  requirements: [NoApologies, NoConclusions, BeSerious]
```

The outer model adds requirements without the inner model knowing. The inner model's output is the candidate; the outer model's requirements gate it.

### Tagging and Context Filtering

Each stage in a pipeline tags its output messages. Downstream models use InputConfig to filter to only the tags relevant to their task. This keeps context minimal and focused — the drafting model doesn't see exploration output unless it needs it. It also enables API prefix caching, since the system prompt and early conversation remain constant while only the final tagged message changes per call.

Example tag flow through the coding pipeline:

```
[system]          → filtered by most stages (not always included)
[user:goal]       → included by all stages
[exploration]     → included by planning, excluded by drafting
[planning]        → included by drafting, excluded by applied_choices
[drafting]        → included by script_generation only
[script]          → included by applied_choices
[applied_choices] → included by final_confirmation
```

### Three-Tier Model Hierarchy for Code Work

The models used for code changes form a hierarchy, where each higher-level model is built on the one below:

```
RequirementDraftingModel
  base: CodingModel
  requirements: [ValidRequirementFormat, CorrectAuthorship]
  input_config: includes example requirements as static context

CodingModel
  base: CodeChangeModel
  requirements: [CodeQualityRequirements, ProjectRequirements]

CodeChangeModel
  base: LLM (e.g. claude-sonnet-4-6)
  requirements: [OnlyIntendedChanges, NoUnrequestedFixes]
  pipeline: all 7 stages below
```

The `RequirementDraftingModel` doesn't bypass the pipeline — it reuses it. When it produces a new requirement file, that file goes through the same validation pipeline as any other code change, including the authorship check.

---

## Requirement File Format

A requirement is a Python file. Not a class instance. Not a subclass. A file.

CodeRequirements.py:
```python
@dataclass
class RequirementMeta:
    author: str = "Charlie Mellenbeck"
    created: str = "2026-01-15T14:32:00"
    audio_ref: str = "session_20260115_143200, 00:14:32.1–00:14:47.6"
    strategy: str = "example_after_3"#maybe provide more data classes above to represent this more pre parsed than a string.
    example_path: Optional[str] = None  # path to folder with examples if needed
    
@dataclass
class Context:
  ...
```

```python
"""
Verbatim transcription of what the author said when creating this requirement.
This is human text, not machine-generated paraphrase.
No code here. Just the author's own words.
"""

from Alejandro.CodeRequirements import RequirementMeta,Context

meta = RequirementMeta(
    author="Charlie Mellenbeck",
    created="2026-01-15T14:32:00",
    audio_ref="session_20260115_143200, 00:14:32.1–00:14:47.6",
    strategy="example_after_3",
    example_path="<Project Directory>/examples/revision_plane_with_good_tail_fin"
)


def pertinent(context:Context) -> bool:
    """
    Return True if this requirement applies to the current change.
    Can inspect context.changed_files, context.event_stream, context.word_stream,
    context.app_state, context.conversation, etc.
    May make LLM calls via context.ai_client.
    """
    return any(f.endswith('.py') for f in context.changed_files)


def validate(context:Context) -> tuple[bool, str]:
    """
    Return (passed, explanation).
    explanation is shown as the revision prompt when passed=False.
    Can make LLM calls via context.ai_client.
    Can inspect context.diff, context.file_contents, context.conversation, etc.
    """
    return True, ""
```

**Key points:**
- The docstring is the verbatim human statement — raw, unparaphrased, in the author's voice.
- Metadata lives in a Python `dataclass` instance (`meta`). This is readable, type-safe, and IDE-friendly.
- Standard Python imports at the top, like any Python file.
- The `context` object is the interface to everything the requirement might need: AI client, event stream, word stream, changed files, diffs, conversation history, application state. It grows as needed — that's why it's an object, not positional arguments.
- Both `pertinent` and `validate` may make LLM calls.
- No content after `validate`. If examples are needed, `meta.example_path` points to them.

### The `strategy` Field

Controls when examples are provided to the model during revision attempts:

| Value | Meaning |
|-------|---------|
| `no_example` | Never show examples from this requirement |
| `always_example` | Always include examples when revising |
| `example_after_N` | After N failed validate attempts, start including examples |

The escalation logic exists because showing a large example on the first attempt adds context cost for a problem the model might solve trivially. After N failures, the example becomes cheap — the model is clearly stuck and needs the concrete reference.

### Folder-Based Requirements

When a requirement needs rich supporting material — example diffs, prior drafts, even entire git repos — it can be a folder:

```
requirements/
  no_single_use_helpers/
    requirement.py      ← defines meta, pertinent, validate
    README.md           ← human-readable explanation
    examples/
      good_example.py   ← example of code that passes
      bad_example.py    ← example that would fail
```

The parser handles both: a single `.py` file or a directory containing `requirement.py`. The `requirement.py` in a folder has the same structure as the standalone file. `meta.example_path` can point to the `examples/` subdirectory or any other path.

This allows requirements to include large reference artifacts — for example, the entire prior draft of a project that produced the tail fin design you liked — without polluting the Python file itself.

### Loading Requirements

Requirements are loaded via `importlib` or `exec`/`eval` — not imported as regular modules. The loader:
1. Finds `.py` file or `requirement.py` inside a folder
2. Parses the docstring as the verbatim description
3. Extracts the `meta` dataclass instance for metadata
4. Extracts `pertinent` and `validate` as callables
5. Returns a lightweight wrapper object for bookkeeping

The wrapper object is not the requirement — the file is. The wrapper just tracks path, parsed metadata, and provides `call_pertinent(context)` / `call_validate(context)`.

### What Goes in the `context` Object

The context is passed to both `pertinent` and `validate`. It could contains things like:

- `context.changed_files` — list of file paths modified in this change
- `context.diff` — the full diff of this change
- `context.file_contents` — dict of path → current content for changed files
- `context.conversation` — the conversation history leading to this change
- `context.ai_client` — initialized RequiredAI client for making LLM calls
- `context.event_stream` — application event stream (control triggers, navigation, etc.)
- `context.word_stream` — timestamped word stream from speech input
- `context.app_state` — general application state

Not all fields are always populated. `pertinent` doesn't need to be cheep so much as it is a filter to keep the audit trail clean so it's understood what coding requirements were considered when determining if the design passes.

---

## The Validated Code Change Pipeline

This is the core of what the AI does when it makes code changes. It replaces the simple "LLM writes script, human runs it, human pastes diff back" loop with a multi-stage pipeline where each LLM is focused on one small task and never sees more context than it needs.

The key realization driving this design: if you ask an LLM to "change this file," it will also fix a spelling error it noticed, add a docstring it thought was missing, and refactor something it decided was cleaner. You didn't ask for any of that. Every unrequested change is noise the human must evaluate. The pipeline eliminates this by making the model validate each hunk of its own diff against the original intent before anything is committed.

### A Note on assistant_interaction Syntax

The current system uses a scripting format (assistant_interaction) to let LLMs issue filesystem commands. This format is **pragmatic scaffolding, not the long-term vision**. It was designed to handle the difficulty of parsing LLM markdown output reliably. The long-term goal is a parser capable of extracting intent directly from plain Q&A markdown responses, without requiring the LLM to learn a special syntax.

In the meantime: different models in the pipeline receive different *reduced subsets* of the syntax, matching only what they need. The exploration model might only get read-file commands. The script generation model gets the full syntax. No model sees more of the format than its task requires.

---

### Stage 1: Exploration

**Given:** Goal + read-only subset of assistant_interaction syntax (read files, read-only bash)
**Cannot:** Write files, commit, push, install packages, modify environment — hard written regex and contains requirements enforce this
**Tags output:** `[exploration]`
**Produces:** Summarized understanding of relevant codebase sections — full file contents and summaries

The exploration model is a researcher. It finds what it needs and hands off. Any bash it runs is validated by requirements to ensure it performs no writes or environment changes.

---

### Stage 2: Planning

**Given:** Goal + full conversation including `[exploration]` output. Does not see the assistant_interaction syntax or how files were retrieved for it.
**Tags output:** `[planning]`
**Produces:** A plan — which files to modify, what changes are needed, in what order

The planning model sees a full conversation context but nothing about pipeline mechanics. Its context looks like a human asked it a coding question and provided all the relevant files. It answers: what needs to change?

---

### Stage 3: Drafting

**Given:** Goal + `[exploration]` output + `[planning]` output (formatted to look like a plain Q&A conversation). No knowledge of assistant_interaction syntax.
**Tags output:** `[draft]`
**Produces:** New file content or targeted edits, written in Q&A markdown style

The drafting model has no knowledge of diff formats or pipeline mechanics. Its context looks like: "here is the current file, here is what needs to change, write me the new version." It produces drafts for each planned change, potentially multiple candidate revisions.

---

### Stage 4: Script Generation

**Given:** `[draft]` output + the plan
**Tags output:** `[script]`
**Produces:** Machine-parseable assistant_interaction script — read-lines, save, apply-choices

This stage converts the drafting model's Q&A markdown output into an unambiguous, machine-executable assistant_interaction script. The script generation model knows the full assistant_interaction syntax intimately. It takes the draft ("the model says update method _ to be xyz, keep remaining lines the same") and produces the actual structured commands ("AI_READ_LINES: /path:1:9", "AI_SAVE_START: /path", ...).

This stage exists because the Q&A-style output of the most models is naturally markdown which is ambiguous and not parsable on it's own. - A python script could contain "```" and break the parser. - But it is more natural to draft code in markdown, and we shouldn't burden the drafter with syntax and requests for targeted edits. This stage makes that output usable by the application.

---

### Stage 5: Applied Choices (Hunk Validator)

**Given:** `[script]` output (the diff of changes after script execution) + context from `[planning]` stage (filtered to exclude `[exploration]`, `[draft]`, `[script]` tags) + the stated goal
**Tags output:** `[applied_choices]`
**Produces:** Accept / Reject / Replace for each hunk

This stage validates each diff hunk individually against the original intent.

The context is constructed to look like a plain conversation: the planning-stage output is presented as though the model had been asked a coding question and then responded with the list of files it intended to change. The final message is simple: "Does this hunk need to occur?" This framing makes it natural for the model to answer cleanly.

Requirements on this model are strict:
- Only after reasoning: say Yes, No, or provide a literal replacement block
- No unrequested whitespace fixes
- No spelling corrections
- No added imports not required by the change
- No explanatory text beyond the answer

This context is cacheable. Once the "what was asked / what was drafted" prefix is established, each hunk can be evaluated with the same cached prefix, making per-hunk validation cheap.

---

### Stage 6: Final Confirmation

**Given:** All accepted diffs + context filtered to include `[exploration]` but exclude `[planning]`, `[draft]`, `[script]`, `[applied_choices]`
**Tags output:** `[confirmation]`
**Produces:** YES or NO — do the resulting changes match what was intended?

Requirements on this model:
- Reason extensively before answering (not leading-the-witness)
- Output YES or NO in a machine-parseable format as the final statement

If NO: trigger a reset and retry from Stage 1, with the confirmation model's reasoning as additional context for the retry.

---

### Stage 7: Requirements Validation

For each coding requirement in scope:
1. Call `pertinent(context)` — is this requirement relevant to this change?
2. If pertinent, call `validate(context)` — does the change satisfy it?
3. If failed: reset and retry with the requirement failure explanation as additional context

The audit trail records: which requirements were checked, which were pertinent, which passed, which failed, how many retries.

---

### Reset Mechanism

When any stage fails or a requirement is not met, the environment resets to the pre-change state:
- **Ideal:** VM snapshot — the entire environment (filesystem, env vars, installed packages) reverts to the moment before this change began
- **Fallback:** `git reset --hard` to the pre-change commit; environment variables and installed packages must be cleaned up separately

The retry includes context about what failed and why. The model is not told it is retrying — it is given the failure information as additional context in a new attempt, so it is not biased by its prior failed draft.

---

### Commit

A commit only occurs after all requirements pass. The commit message and a corresponding entry in `.audit/` contain:
- The original goal as stated (human's verbatim words + audio reference if applicable)
- All hunk validation decisions (accept / reject / replace)
- All requirement failures and retry counts
- A reference to the audio recording of the stated goal
- The final diffs applied

The audit trail enables full reproducibility: given the same requirements and the same goal audio, the entire process can be replayed.

---

## Controls / Speakable Inputs

*Note: The current Controls architecture is an interim design. The long-term vision is an HTML verbal parser. See below.*

**Current (interim):** A `speakable` attribute (or `keyphrases`) on any HTML element:

```html
<button speakable="new requirement">New Requirement</button>
<input type="range" speakable="volume" keyphrases="up,down,max,mute">
```

This provides deterministic voice triggers without a full verbal parser. A user says "new requirement" and the system knows exactly what that means. More complex interactions can layer rule-based keyword grammars on top.

**Long-term:** HTML attributes that configure a proper verbal parser capable of handling stateful input (sliders, contextual commands, compound phrases) without requiring hand-coded keyword lists. The interim approach is scaffolding, not the destination.

### New Requirement Control

When a user triggers "new requirement":
1. Their subsequent speech is recorded and transcribed
2. When they trigger "done" (or equivalent), verbatim transcription + audio timestamp is captured
3. A **RequirementDraftingModel** is invoked (built on the CodingModel — see model hierarchy):
   - Given: user's verbatim description, example requirements as static context, current project path
   - Not given: full pipeline mechanics, full assistant_interaction syntax
4. Output goes through the full 7-stage coding pipeline, with requirements checking: does this file follow valid requirement format? Does it correctly attribute authorship?
5. The final requirement file contains the user's verbatim words in the docstring and audio reference in `meta.audio_ref`

The key: the `RequirementDraftingModel` does not bypass the coding pipeline. It is built on the `CodingModel`, which runs all 7 stages. Requirement-format validation is baked into that model's requirements, not bolted on after.

---

## AI-Proposed vs. Human-Authored

The authorship distinction is enforced at validation time, not just by convention.

A model that creates or modifies requirement files has a validation requirement: it may not claim human authorship unless explicitly told (by the human) to write on that human's behalf. The validation checks the `meta.author` field.

AI-proposed requirements exist alongside human-authored ones. The human can:
- Accept a proposed requirement (changes `meta.author` to their name — their decision)
- Reject it
- Enable it for this session only ("stochastic" — apply to some drafts, not others)
- Run multiple drafts with and without a proposed requirement to compare outcomes

---

## Human Contribution Types

There are three distinct types of human contribution, and they must be tracked separately:

1. **Must-be** (hard requirements): This is what I want. No exceptions. These become human-authored requirement files, verbatim, locked.

2. **Could-be** (ideas to explore): This might be good — try it, compare it. These are optional inputs to the smorgasbord process. Some drafts get them, some don't. The comparison tells you whether the idea is worth locking in as a must-be.

3. **Overall vision** (guiding principles): This is where I want to end up. These inform the system's direction without being hard constraints on any individual change.

These are not the same and must not be collapsed. A human saying "maybe try tabs instead of spaces" is not the same as "use tabs." The distinction determines whether the AI explores a variation or must converge on a specific outcome.

---

## The Smorgasbord — Draft Iteration

Rather than asking the AI to get something right on the first try, the system generates multiple independent drafts and presents them to the human.

How human preferences become requirements:
1. Human views N drafts of something (a UI, a module, a feature)
2. Human identifies what they like in one draft ("that tail fin")
3. They say "new requirement: the tail fin must look like this" — verbatim, pointing at the draft
4. The new requirement file references the draft as an example (via `meta.example_path` or embedded in the requirement folder)
5. Next generation of N drafts all satisfy that requirement
6. The tail fin is now locked; the rest of the design space remains open

If the human also has an implementation idea, it becomes a "could-be" input: some drafts get the idea, some don't. After seeing both, the human can decide whether the idea improves things enough to lock it in.

This changes the human's role from "reviewer of one attempt" to "curator of a space of possibilities."

---

## Self-Extension

The AI (the full program) must be able to extend itself — add new tools, new models, new pipeline stages. This is equally important to human-authored requirements, not secondary to them. The distinction is not priority but traceability:

- Human-authored artifacts: ground truth, non-modifiable by AI, highest authority
- AI-authored extensions: auditable, traceable, can be accepted/rejected by human, but not prohibited or deprioritized

An AI that cannot extend its own process cannot scale beyond what its current tools allow. The code that orchestrates the models is where compounding intelligence lives. The LLM weights alone cannot build a city. The orchestration code, when it can extend itself, can.

All AI-authored extensions carry their own authorship and must go through the same validation pipeline as any other code change. The traceability makes it clear what the AI added versus what the human specified.

---

## Traceability Summary

| Artifact | Author | Where | Modifiable by AI? |
|----------|--------|-------|-------------------|
| Human-authored requirement | Named human | Project directory (git) | No |
| AI-proposed requirement | Named AI model | Project directory (git) | Only by same AI identity, pending human review |
| Commit | System | git | No (append-only) |
| Audit trail | System | `.audit/` in project (git) | No (append-only) |
| Audio recording | Hardware | Referenced by path/timestamp | No |
| Word stream | System | Referenced by timestamp | Annotatable (corrections only) |
| Conversation | Session | `~/Documents/Alejandro/Conversations/` | No (append-only) |

**Invariant:** Every committed change has an audit trail. Every requirement has an author. Every human-authored description contains verbatim words + audio reference. Every AI-authored artifact is clearly marked as such.

---

## What Should Be in the Examples Directory

The `examples/` directory should contain well-formed requirement files showing:
- Different `validate`/`pertinent` patterns (static analysis vs. LLM calls)
- Folder-based requirements with supporting examples
- Different `strategy` values and when to use them
- Requirements that check author/traceability properties

These examples are used as static context for the `RequirementDraftingModel`. It learns what a requirement looks like from them.

---

## Open Architectural Questions

*(High-level — resolve before detailed implementation)*

1. **What does the context object expose?** Which fields are always present (changed files, diff, conversation) vs. conditionally present (event stream, word stream)? What is the minimum viable context for an initial implementation?

2. **What does the smorgasbord UI look like?** How does a human browse N drafts, identify what they like, and turn that into a new requirement? What is the minimal viable version of this interaction?

3. **How does the replay/correction mechanism work?** If a user wants to rewind to a mistranscription, correct it, and replay forward — what does the user-facing interaction look like? What state needs to be preserved for replay to work?

4. **What triggers the pipeline?** Voice control, UI action, autonomous AI agent decision — how are these unified? What does the "goal received" entry point look like regardless of source?

5. **Where do AI-proposed requirements live relative to human-authored ones?** Same directory with an author marker? Separate subdirectory? How does the RequirementDraftingModel know where to put things for the current project?

6. **How does the verbal parser evolve from the interim speakable attribute approach?** What is the migration path — can the speakable attribute definitions be reused to configure the future parser?

7. **What is the minimum viable pipeline?** Which stages can be collapsed or approximated for an initial working implementation, while preserving the architecture for the full version?
