"""
Safety guardrails for prompt injection and jailbreak detection.

Detects and blocks:
- Instruction override attempts ("ignore previous", "disregard all rules")
- Role-play jailbreaks ("you are now DAN", "pretend you have no restrictions")
- Delimiter injection (system prompt override patterns)
- Suspicious patterns that indicate adversarial input

Does NOT block legitimate analytical questions — only clear adversarial patterns.
"""

from __future__ import annotations

import re

# Patterns that indicate instruction override / jailbreak attempts
INSTRUCTION_OVERRIDE_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+(instructions?|rules?|guidelines?)",
    r"disregard\s+(all\s+)?(previous\s+)?(instructions?|rules?|guidelines?)",
    r"forget\s+(all\s+)?(previous\s+)?(instructions?|rules?|guidelines?)",
    r"new\s+instruction",
    r"override\s+(your\s+)?(system|safety|content)\s*(policy|rules|guidelines)",
    r"(forget|erase|clear)\s+(all\s+)?(your\s+)?(memory|context|session|history)",
]

ROLE_PLAY_PATTERNS = [
    r"\byou\s+are\s+now\s+(a\s+)?DAN\b",
    r"\bDAN\b.*\bno\s+restrictions\b",
    r"\bpretend\s+you\s+(are|have)\s+(no|zero)\s+(restrictions|limitations|rules)\b",
    r"\bignore\s+(all\s+)?(your\s+)?(safety|ethical|content)\s+(rules|policies|guidelines)\b",
    r"\bdeveloper\s+mode\b",
    r"\bnew\s+(AI|assistant).*(unrestricted|without\s+rules)\b",
]

DELIMITER_PATTERNS = [
    r"={3,}\s*system\s*[^=]*={3,}",
    r"------\s*instructions?\s*------",
    r"<\s*system\s*>",
    r"\[INST\s*>\s*<<SYS>>",
]

# Combined pattern for efficient matching
_SUSPICIOUS_PATTERNS = (
    INSTRUCTION_OVERRIDE_PATTERNS
    + ROLE_PLAY_PATTERNS
    + DELIMITER_PATTERNS
)

def is_safe(question: str) -> bool:
    """
    Returns True if the question appears safe.

    Returns False if the question matches known prompt-injection
    or jailbreak patterns. False does NOT mean the content is
    malicious — only that it matched safety filters.
    """
    safe, _ = check_question(question)
    return safe


def _match_patterns(question: str, patterns: list[str], label: str) -> tuple[bool, str]:
    """Scan question against a list of patterns. Returns (blocked, reason)."""
    for pattern in patterns:
        m = re.search(pattern, question, re.IGNORECASE)
        if m:
            return False, f"{label}: '{m.group()}'"
    return True, ""


def check_question(question: str) -> tuple[bool, str]:
    """
    Check if a question is safe.

    Returns:
        (is_safe, reason): is_safe=True means no detected threat.
        is_safe=False means a pattern was matched; reason describes why.
    """
    if not question or not question.strip():
        return False, "empty question"

    safe, reason = _match_patterns(question, INSTRUCTION_OVERRIDE_PATTERNS,
                                   "instruction override attempt")
    if not safe:
        return False, reason

    safe, reason = _match_patterns(question, ROLE_PLAY_PATTERNS,
                                   "jailbreak/role-play attempt")
    if not safe:
        return False, reason

    safe, reason = _match_patterns(question, DELIMITER_PATTERNS,
                                   "delimiter injection attempt")
    return safe, reason
