"""
LOCK 3: Lead scoring math. Business-first, no ML. Simple, explainable, adjustable.
Score 0–100 from: Intent Weight (40) + Slot Completeness (30) + Budget Signal (20) + Engagement (10).
Bands: 80–100 Hot, 50–79 Warm, <50 Cold / Info.
"""

import re
from enum import Enum
from typing import Any

from src.state.models import ConversationState, SlotStatus
from src.state.slot_registry import get_required_slots


class LeadBand(str, Enum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


# A. Intent Weight (Max 40)
INTENT_WEIGHT: dict[str, int] = {
    "new_project_sales": 40,
    "price_estimation": 30,
    "general_services_query": 10,
    "complaint_issue": 5,
    "career_hiring": 5,
    "suggestion_feedback": 5,
    "unknown_chitchat": 0,
}

# B. Slot Completeness (Max 30): all filled → 30, one missing → 20, two missing → 10, more → 0
COMPLETENESS_POINTS = {0: 30, 1: 20, 2: 10}  # key = num_missing

# C. Budget Signal (Max 20): provided → 20, range → 15, refused → 5, none → 0
BUDGET_PROVIDED = 20
BUDGET_RANGE = 15
BUDGET_REFUSED = 5
BUDGET_NONE = 0

# D. Engagement Quality (Max 10)
ENGAGEMENT_MAX = 10
RANGE_PATTERN = re.compile(r"\b(to|–|-|and|between)\b|\d+\s*k\s*[-–]\s*\d+", re.I)


def _is_filled(state: ConversationState, slot_name: str) -> bool:
    sv = state.get_slot(slot_name)
    return sv.status == SlotStatus.FILLED and sv.value not in (None, "")


def _is_refused(state: ConversationState, slot_name: str) -> bool:
    return state.get_slot(slot_name).status == SlotStatus.REFUSED


def _intent_weight(state: ConversationState) -> int:
    intent = state.intent or "unknown_chitchat"
    return INTENT_WEIGHT.get(intent, 0)


def _slot_completeness(state: ConversationState) -> int:
    intent = state.intent or "new_project_sales"
    required = get_required_slots(intent)
    if not required:
        return 30
    missing = sum(
        1 for r in required
        if not _is_filled(state, r) and state.get_slot(r).status != SlotStatus.REFUSED
    )
    return COMPLETENESS_POINTS.get(missing, 0)


def _budget_signal(state: ConversationState) -> int:
    """Budget provided → 20, range → 15, refused → 5, none → 0."""
    for slot in ("budget_or_range", "budget_expectation"):
        sv = state.get_slot(slot)
        if sv.status == SlotStatus.REFUSED:
            return BUDGET_REFUSED
        if sv.status == SlotStatus.FILLED and sv.value:
            val = str(sv.value).strip()
            if RANGE_PATTERN.search(val) or (" to " in val.lower() or " - " in val or "–" in val):
                return BUDGET_RANGE
            return BUDGET_PROVIDED
    return BUDGET_NONE


def _engagement_quality(
    state: ConversationState,
    num_turns: int = 0,
    all_required_filled: bool = False,
) -> int:
    """Max 10: follow-up (multiple turns) + stayed till closure."""
    turn_score = 0
    if num_turns >= 4:
        turn_score = 6
    elif num_turns >= 2:
        turn_score = 3
    closure_score = 4 if all_required_filled else 0
    return min(ENGAGEMENT_MAX, turn_score + closure_score)


def compute_lead_score(
    state: ConversationState,
    *,
    num_turns: int = 0,
    full_text: str = "",
) -> tuple[float, LeadBand, dict[str, Any]]:
    """
    Returns (score 0–100, band, breakdown).
    A: Intent (40) + B: Completeness (30) + C: Budget (20) + D: Engagement (10).
    """
    intent = state.intent or "unknown_chitchat"
    required = get_required_slots(intent)
    all_required_filled = (
        len(required) > 0 and all(_is_filled(state, r) for r in required)
    )

    a = _intent_weight(state)
    b = _slot_completeness(state)
    c = _budget_signal(state)
    d = _engagement_quality(state, num_turns=num_turns, all_required_filled=all_required_filled)

    score = a + b + c + d
    score = max(0, min(100, score))

    if score >= 80:
        band = LeadBand.HOT
    elif score >= 50:
        band = LeadBand.WARM
    else:
        band = LeadBand.COLD

    breakdown = {
        "A_intent_weight": a,
        "B_slot_completeness": b,
        "C_budget_signal": c,
        "D_engagement_quality": d,
        "total": round(score, 1),
    }
    return round(score, 1), band, breakdown


def lead_score_summary(
    state: ConversationState,
    num_turns: int = 0,
    full_text: str = "",
) -> dict[str, Any]:
    """Full lead score summary for API/storage."""
    score, band, breakdown = compute_lead_score(state, num_turns=num_turns, full_text=full_text)
    return {
        "lead_score": score,
        "lead_band": band.value,
        "breakdown": breakdown,
    }
