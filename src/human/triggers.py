"""
Phase 8: Human takeover triggers.
Intent confidence < threshold, user frustration, complaint intent.
"""

import re

# Confidence threshold below which we flag for human
CONFIDENCE_THRESHOLD = 0.5

# Simple frustration signals (expand with ML later)
FRUSTRATION_PATTERN = re.compile(
    r"\b(frustrated|angry|terrible|worst|horrible|unacceptable|ridiculous|again\?|still not)\b",
    re.I,
)


def needs_human_takeover(
    intent_confidence: float | None,
    intent: str | None,
    full_text: str,
) -> tuple[bool, list[str]]:
    """
    Returns (needs_human, list of trigger reasons).
    """
    reasons: list[str] = []
    if intent_confidence is not None and intent_confidence < CONFIDENCE_THRESHOLD:
        reasons.append("low_confidence")
    if intent == "complaint_issue":
        reasons.append("complaint_intent")
    if full_text and FRUSTRATION_PATTERN.search(full_text):
        reasons.append("frustration_detected")
    return (len(reasons) > 0, reasons)
