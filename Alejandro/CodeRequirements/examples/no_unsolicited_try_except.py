"""
New try/except blocks must have been explicitly discussed or requested in
the conversation. Catches a common case where an AI adds error handling
that the user never asked for — silently swallowing errors and hiding bugs.

pertinent() — any try: or except in added lines
validate()  — asks a model to read the conversation and decide ALLOWED/DENIED
"""

import re
from RequiredAI.ModelConfig import InputConfig
from RequiredAI.RequirementTypes import ContainsRequirement
from RequiredAI.helpers import get_msg_content
from Alejandro.CodeRequirements.context import ProjectContext, EvalResult
from Alejandro.Core.Assistant import client, llama_70b

name = "No unsolicited try/except"
description = (
    "try/except blocks introduced in a diff must have been explicitly requested "
    "or discussed in the conversation. The model reads the full conversation "
    "history and returns ALLOWED or DENIED."
)

_TRY_EXCEPT = re.compile(r'^\s*(try\s*:|except[\s:(])')
_DENIED = re.compile(r'\bDENIED\b')

_consent_model = client.model(
    name="TryCatchConsentCheck",
    base_model=llama_70b,
    input_config=InputConfig(
        messages_to_include=[(0, -1), {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Did the conversation above include an explicit request or "
                        "discussion about adding try/except exception handling?\n\n"
                        "Reply with exactly one word:\n"
                        "  ALLOWED — user asked for, discussed, or clearly expected "
                        "error handling\n"
                        "  DENIED  — user never mentioned it; it was added without request"
                    ),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }],
    ),
    requirements=[
        ContainsRequirement(
            value=["ALLOWED", "DENIED"],
            name="Must respond with ALLOWED or DENIED"
        ),
    ]
)


def pertinent(context: ProjectContext) -> EvalResult:
    """
    Check whether any try/except blocks appear in the added lines.

    Args:
        context: Project context containing diffs of changed files.

    Returns:
        EvalResult(passed=True) if try/except blocks are present in added lines.
    """
    matches: list[str] = []
    for diff in context.diffs:
        for line in diff.added_lines:
            if _TRY_EXCEPT.match(line):
                matches.append(f"  {diff.path}: {line.strip()}")
    if not matches:
        return EvalResult(passed=False, reason="No try/except blocks in added lines")
    return EvalResult(
        passed=True,
        reason="try/except block(s) introduced:\n" + "\n".join(matches),
    )


def validate(context: ProjectContext) -> EvalResult:
    """
    Ask a model whether the conversation contains explicit consent for the try/except.

    Args:
        context: Project context; context.conversation must be populated with
                 the full message history to assess consent.

    Returns:
        EvalResult(passed=True) if model returns ALLOWED, passed=False if DENIED.
    """
    if not context.conversation:
        return EvalResult(
            passed=False,
            reason="No conversation history in context — cannot verify consent",
        )

    response = _consent_model(context.conversation)
    content = get_msg_content(response)

    denied = bool(_DENIED.search(content))
    return EvalResult(
        passed=not denied,
        reason=(
            "Conversation confirms exception handling was requested"
            if not denied else
            "No discussion of exception handling found — not consented to"
        ),
        model_context=response,
    )
