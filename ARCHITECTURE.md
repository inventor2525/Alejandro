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

2. **Human time is the bottleneck, not AI compute.** AI is infinitely parallelizable — add more instances, more GPUs, more API calls. The constraint is how fast a human can speak, read, and decide. If something is mistranscribed or misunderstood, the cost falls entirely on the human who must re-say it. Design must minimize human re-work, not AI compute.

3. **When intent is ambiguous, run a jury — don't ask the human yet.** If something a human said could be interpreted multiple ways, spawn multiple agents and compare their interpretations. If all 10 agents agree, run with it. If they diverge, that's a genuine question worth raising to the human. The human should only be interrupted when no amount of AI review resolves the ambiguity.

4. **Everything is a stream, and every stream is traceable.** Audio, transcription, tool calls, application events, key presses, pen strokes — all are streams. Everything is timestamped and recorded. Any session can be replayed from any point, with corrections applied forward from the correction point. A mistranscription is fixable because the audio still exists.

5. **LLMs are Q&A machines.** They are excellent at answering one focused question with constrained context. They are poor at building an airplane. They will always be. The way to build an airplane is to decompose it into 10,000 individual Q&A problems and chain the answers together. Scaling to a city means scaling the decomposition process itself — not the LLM.

6. **Requirements are code.** A requirement is a Python file with a `validate()` function and a `pertinent()` function. They are executable, committed to git, versioned, and auditable. They are not configuration or documentation — they are first-class program artifacts.

7. **Models are nestable.** A "model" in this system is not a raw LLM. It is an LLM (or another model) combined with requirements and an input configuration. Models compose: a medical advice model can be built on top of a direct-speech model, inheriting its tone while adding domain constraints. Any model exposes a standard OpenAI-compatible interface so it can be used as a base for another model.

---

## Everything Is a Stream

The system is best understood as a set of parallel streams, all timestamped and recorded:

| Stream | Contents |
|--------|----------|
| Audio stream | Raw audio bytes from microphone or playback |
| Word stream | Timestamped transcribed words (linked list of WordNodes) |
| Command/event stream | Tool calls, AI script commands, control triggers, navigation events |
| Pen/touch stream | Screen touch events, pen strokes (future) |
| Conversation stream | Messages exchanged with LLM models |

These streams run in parallel and all reference the same timeline. An audio timestamp in a requirement file links back to the word stream which links back to the audio stream. If the transcription was wrong, the audio is still there. A better transcription model applied later can correct it.

The goal is that any development session can be replayed entirely — the file tree rebuilt from scratch by replaying the command stream. If you want to correct a decision made after a mistranscription, you correct the mistranscription, then replay forward from that point.

---

## Author Model

Every artifact has a specific author. Not "human" vs "AI" — a named author with identity and context.

Examples:
- `author: Charlie Mellenbeck`
- `author: Claude-claude-sonnet-4-6`
- `author: Claude-claude-opus-4-6 (proposed, pending review)`

When a human creates a requirement by speaking, their verbatim words (as transcribed) go directly into the requirement's description field. The audio timestamp range is also recorded so the original audio can be retrieved — both for traceability and because a better transcription might later be available. If the user explicitly instructs the AI to write a requirement on their behalf, their words are still copied verbatim and attributed to them. The AI never paraphrases a human's stated intent into a requirement unless the human reviews and approves that paraphrase.

AI-authored artifacts (proposed requirements, drafted code) are never falsely attributed to a human author. The validation pipeline enforces this — a model tasked with placing requirements checks that any requirement it creates carries its own authorship, not a human's name, unless it was explicitly told to create on that human's behalf.

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

**Nestability**: A model can be built on top of another model. The outer model adds requirements without the inner model knowing. The inner model's output is the candidate; the outer model's requirements gate it.

```
TalkModel
  base: DirectSpeechModel
  requirements: [NoApologies, NoOverExplaining, NoKissUp]

DirectSpeechModel
  base: anthropic/claude-sonnet-4-6
  requirements: [NoConclusions, BeSerious]
```

A model built on RequiredAI models exposes a standard OpenAI-compatible endpoint. Additional fields beyond the OpenAI standard (like `requirements` passed at call time) are supported within the framework but transparent to callers that don't use them.

---

## Requirement File Format

A requirement is a Python file. Not a class instance. Not a subclass. A file.

```python
"""
author: Charlie Mellenbeck
created: 2026-01-15T14:32:00
audio_ref: session_20260115_143200, 00:14:32.1–00:14:47.6
description:
    No helper functions that are only called from one place.
    The logic should live inline unless it is reused or the
    function name itself carries meaningful documentation value.
strategy: no_example
"""
from required_ai_client import RequiredAIClient  # or whatever is on the context object


def pertinent(context) -> bool:
    """
    Return True if this requirement applies to the current change.
    Can inspect context.changed_files, context.event_stream, context.word_stream,
    context.app_state, context.conversation, etc.
    """
    return any(f.endswith('.py') for f in context.changed_files)


def validate(context) -> tuple[bool, str]:
    """
    Return (passed, explanation).
    explanation is shown as the revision prompt when passed=False.
    Can make LLM calls via context.ai_client.
    Can inspect context.diff, context.file_contents, context.conversation, etc.
    """
    # implementation using whatever is needed
    return True, ""
```

**Key points:**
- Standard Python imports at the top, like any Python file.
- The `context` object is the interface to everything the requirement might need: AI client, event stream, word stream, changed files, diffs, conversation history, application state. It grows as needed — that's why it's an object, not positional arguments.
- Both `pertinent` and `validate` may make LLM calls. `pertinent` should be cheap in most cases, but it's not prohibited from doing more.
- The file docstring is machine-parsable: `author`, `created`, `audio_ref`, `description`, `strategy` are recognized fields. Everything after a `---` separator at the bottom of the file is markdown and is stripped before execution.
- Requirements can include rich content below the separator: example code, conversation history, even entire previous drafts. These are reference material for humans and for the AI when `strategy` directs it to use examples.
- A requirement can be a **folder** when the examples or supporting content are too large or numerous for a single file. The parser handles both: single `.py` file or directory with a `__init__.py` defining `pertinent` and `validate`.

### strategy field

Controls when examples are provided to the AI during validation revision:

| Value | Meaning |
|-------|---------|
| `no_example` | Never show examples from this file |
| `always_example` | Always include examples from below the separator |
| `example_after_N` (e.g. `example_after_3`) | Start including examples after N failed attempts |

### Loading requirements

Requirements are loaded via `importlib` or `exec`/`eval` — not imported as regular modules. The loader extracts `pertinent` and `validate` as callables, and parses the docstring header. The key artifact is the file itself, not any serialized object. The loader may produce a lightweight wrapper object for bookkeeping (author, path, parsed metadata), but that object is not the requirement — the file is.

---

## The Validated Code Change Pipeline

This is the core of what the AI does when it makes code changes. It replaces the simple "LLM writes script, user runs it, user pastes diff back" loop with a multi-stage pipeline that keeps each LLM focused on one small task.

The key realization driving this design: if you ask an LLM to "change this file," it will also fix a spelling error it noticed, add a docstring it thought was missing, and refactor something it decided was cleaner. You didn't ask for any of that. Every unrequested change is noise the human must evaluate. The pipeline eliminates this by making the LLM validate each hunk of its own diff against the original intent before anything is committed.

### Stage 1: Exploration

**Given:** Goal + read-only syntax (read files, read-only bash)
**Cannot:** Write files, commit, push, install packages, modify environment
**Produces:** Summarized understanding of relevant codebase sections

The exploration agent is like a researcher. It finds what it needs, summarizes it, and hands off. It is given only a reduced subset of the assistant_interaction scripting syntax. It knows nothing about how to execute changes — only how to read. Any bash executing ability that it may be given, is validated with requirements that make sure it's not trying to modify the environment or produce un-requested code changes.

### Stage 2: Planning

**Given:** Goal + exploration summary containing full files and summaries (full conversation prior, no AI script syntax)
**Produces:** A plan — which files to modify, what changes are needed, in what order

The planning model sees a full context. It does not know how the execution format works, or how files were retrieved for it. It thinks it's answering a simple question: what needs to change? - As though a human had asked it, with all the context it would need.

### Stage 3: Drafting

**Given:** Plan + relevant file excerpts (formatted to look like a plain Q&A conversation)
**Produces:** New file content or targeted edits

The drafting model has no knowledge of assistant_interaction syntax, diff formats, or pipeline mechanics. Its context looks like: "here is the current file, here is what needs to change, write me the new version." It is simply a very good editor.

### Stage 4: Applied Choices (Hunk Validator)

This stage validates each diff hunk individually.

The context for this model is constructed synthetically — it is made to look like a plain conversation where the model had been asked to make a specific change and then responded with the specific changes made to a specific file. The model doesn't know it is in a pipeline. It thinks it's reviewing its own prior response.

For each hunk:
- **Given:** The hunk, the synthetic conversation context (cached, cheap to reuse), the stated goal
- **Requirements on this model:** Only say Yes, No, or provide a replacement block. No explanations. No unrequested changes. No whitespace fixes. No spelling corrections. No added imports not required by the change.
- **Produces:** Accept / Reject / Replace-with for each hunk

This context is cacheable. Once the "what was asked" part is established, each hunk can be evaluated cheaply with the same cached prefix.

### Stage 5: Final Confirmation

**Given:** All accepted diffs + the synthetic conversation context from Stage 4
**Requirements on this model:** Reason extensively before answering. Then output YES or NO in a parseable format.
**Produces:** A confirmation that the resulting changes are what was intended — or not.

If No: reset environment and retry from Stage 1, with context about what was wrong.

### Stage 6: Requirements Validation

For each coding requirement in scope:
1. Call `pertinent(context)` — is this requirement relevant to this change?
2. If pertinent, call `validate(context)` — does the change satisfy the requirement?
3. If failed: retry from reset (git reset, environment snapshot restore) with the requirement failure explanation as additional context.

Only after all requirements pass does a commit occur.

### Reset Mechanism

When any stage fails, the environment is reset to the pre-change state:
- `git reset --hard` to the pre-change commit
- Environment variables, installed packages, etc. ideally via VM snapshot
- The retry includes context about what failed and why

### What a Commit Contains

A commit only occurs after all requirements pass. The commit message includes:
- The original goal as stated (human or AI)
- The audit trail: which requirements were checked, which passed, which failed and how many retries
- A reference to the audio recording of the human's stated goal (if applicable)

The audit trail is also written to a per-project directory (e.g., `.audit/`), where full detail lives even if the commit message is abbreviated.

---

## Controls / Speakable Inputs

The current concept of "Controls" (verbal buttons) generalizes to a `speakable` attribute (or `keyphrases`) on any HTML element:

```html
<button speakable="new requirement" onclick="...">New Requirement</button>
<input type="range" speakable="volume" keyphrases="up,down,max,mute">
```

This gives determinism to verbal input without requiring a full verbal parser. A user can say "new requirement" and the system knows exactly what that means without any LLM interpretation. More complex interactions (sliders, contextual commands) can build rule-based keyword grammars on top of the same mechanism, and fall back to LLM interpretation for open-ended input.

### New Requirement Control

When a user triggers "new requirement":
1. Their subsequent speech is recorded and transcribed
2. When they finish (trigger "done" or equivalent), the verbatim transcription + audio timestamp is captured
3. A **requirement drafting model** is invoked:
   - Given: user's verbatim description, example requirements from the examples directory, current project path
   - NOT given: full pipeline mechanics, assistant_interaction syntax details, etc.
   - Context looks like: "here is how requirements are structured, here is what the user wants, write the Python file"
4. The output goes through the coding pipeline (Stages 4-6) to be placed in the project
5. The validation stage checks: does this requirement falsely claim human authorship when it shouldn't?
6. The final requirement file contains the user's verbatim words in the `description` field and the audio reference in `audio_ref`

The user never has to write Python. They speak. The AI transcribes and drafts. But the human's words are in the file, verbatim, as the source of truth.

---

## AI-Proposed vs. Human-Authored

The authorship distinction is enforced at the validation level, not just by convention.

A model that creates or modifies requirement files has a validation requirement: it may not claim human authorship unless explicitly told (by the human) to write on that human's behalf. The validation checks the `author` field against the known AI model identity.

AI-proposed requirements exist alongside human-authored ones. The human can:
- Accept a proposed requirement (changes `author` to their name — their decision, not the AI's)
- Reject it
- Enable it for this session only
- Run multiple drafts of a project with and without a proposed requirement to compare outcomes

The mechanism for preventing AI modification of human artifacts is application-level enforcement (the validation pipeline rejects changes to human-authored files) combined with git history as an audit trail. The specific enforcement mechanism is less important than the principle: the AI knows it cannot do this because the pipeline will catch it and require a retry.

---

## The "Airplane" Analogy and Why It Matters

A key realization that should inform every design decision:

> LLMs are great at Q&A. They are poor at "build me an airplane." This will not fundamentally change with more parameters. An LLM that could build an airplane couldn't build a city. And a city is not the ceiling.

The way to build an airplane is to ask 10,000 focused Q&A questions and assemble the answers. The way to build a city is to build a process that asks 10,000 focused questions about how to build an airplane, and then runs that process 10,000 times. The process must be able to extend itself.

What this means architecturally:
- Every LLM call should have minimal, focused context. The exploration model doesn't know the diff format. The drafting model doesn't know the validation pipeline. Each model is optimized for one small task.
- The code that orchestrates the models is where the intelligence lives. The LLM weights are one component.
- The system must be able to add new pipeline stages, new models, new tools — and the additions must be traceable.
- AI-initiated extensions to the pipeline (new tools, new models, new pipeline steps) are possible but carry lower priority than human-defined ones. The traceability makes this clear.

---

## The "Smorgasbord" — Drafts and Iteration

Rather than asking the AI to get something right on the first try, the system generates multiple independent drafts and presents them to the human as a set of options.

- The human identifies what they like about each draft
- What they like becomes a new requirement
- The next round of drafts all satisfy that requirement
- The process converges iteratively, with the human contributing only their preferences — not implementation details

This changes the human's role from "reviewer of one attempt" to "curator of a space of possibilities." The AI does the work of exploring that space. The human does the work of knowing what they want when they see it.

---

## Traceability Summary

| Artifact | Author | Where | Modifiable by AI? |
|----------|--------|-------|-------------------|
| Human-authored requirement | Named human | Project directory (git) | No |
| AI-proposed requirement | Named AI model | Project directory (git, marked proposed) | Only by AI that authored it, pending human review |
| Commit | System | git | No (append-only) |
| Audit trail | System | `.audit/` in project (git) | No (append-only) |
| Conversation | Session | `~/Documents/Alejandro/Conversations/` | No (append-only) |
| Audio recording | Hardware | Referenced by path/timestamp | No |
| Word stream | System | Referenced by timestamp | Annotatable (corrections) |

**Invariant:** Every committed change has an audit trail. Every requirement has an author. Every description has a source (verbatim human words + audio reference, or clearly AI-attributed).

---

## What Should Be in the Examples Directory

The `examples/` directory should contain:
- Well-formed requirement files showing different validate/pertinent patterns
- Requirements that use LLM calls vs. static analysis
- Requirements that are folder-based (with supporting examples)
- Requirements with different `strategy` values
- These examples are used as context for the requirement drafting model — it learns what a requirement looks like from them, not from a class definition

---

## Open Architectural Questions

*(High-level questions to resolve before detailed implementation)*

1. **What does the context object look like?** What fields does it expose to `pertinent` and `validate`? Which parts are always present (changed files, diff, conversation) vs. optionally present (event stream, word stream)?

2. **How does the coding pipeline compose with the existing assistant_interaction format?** The intent is to eventually minimize how much any individual LLM knows about the scripting format — but what's the migration path?

3. **What triggers the pipeline?** Is it a voice control ("make this change")? A UI action? An AI agent deciding to make a change autonomously? All of the above, and how are they unified?

4. **How does the replay/correction mechanism work at a user-facing level?** If a user wants to rewind to a mistranscription, correct it, and replay forward — what does that UI look like? What's the minimal viable version?

5. **What does the smorgasbord UI look like?** How does a user browse 10 airplane variants and pick the tail fin they want? What level of granularity makes sense for selection?

6. **Where do AI-proposed requirements live relative to human-authored ones?** Same directory with a marker? Separate directory? How does the requirement drafting model know where to put things for a given project?

7. **How does a model know it's building on top of another RequiredAI model vs. a raw LLM?** Is this transparent in the API? Does it matter to the model consuming it?
