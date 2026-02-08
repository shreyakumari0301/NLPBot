"""
Completeness status — SEPARATE from lead score. Helps sales trust the AI.
Complete | Actionable (minor missing) | Incomplete | Info-only.
"""

from enum import Enum
from typing import Any

from src.state.models import ConversationState, SlotStatus
from src.state.slot_registry import get_required_slots


class CompletenessStatus(str, Enum):
    """Completeness status (separate from score)."""
    COMPLETE = "complete"
    ACTIONABLE = "actionable"  # minor missing
    INCOMPLETE = "incomplete"
    INFO_ONLY = "info_only"


def compute_completeness(state: ConversationState) -> tuple[int, list[str], CompletenessStatus]:
    """
    Returns (completeness_pct 0–100, mandatory_fields_missing, status).
    Status: Complete | Actionable (1–2 missing) | Incomplete | Info-only.
    """
    intent = state.intent or "new_project_sales"
    required = get_required_slots(intent)

    # Info-only: no slots to capture (general query, chitchat)
    if not required:
        return 100, [], CompletenessStatus.INFO_ONLY

    missing: list[str] = []
    filled = 0
    for name in required:
        sv = state.get_slot(name)
        if sv.status == SlotStatus.FILLED and sv.value not in (None, ""):
            filled += 1
        elif sv.status not in (SlotStatus.UNAVAILABLE, SlotStatus.REFUSED):
            missing.append(name)

    pct = round((filled / len(required)) * 100) if required else 100
    pct = min(100, max(0, pct))

    num_missing = len(missing)
    if num_missing == 0:
        status = CompletenessStatus.COMPLETE
    elif num_missing <= 2:
        status = CompletenessStatus.ACTIONABLE
    else:
        status = CompletenessStatus.INCOMPLETE

    return pct, missing, status


def completeness_summary(state: ConversationState) -> dict[str, Any]:
    """Full completeness summary for API/storage."""
    pct, missing, status = compute_completeness(state)
    return {
        "completeness_pct": pct,
        "mandatory_fields_missing": missing,
        "status": status.value,
    }


# Backward compatibility: alias for code that expected CompletenessLabel
CompletenessLabel = CompletenessStatus
