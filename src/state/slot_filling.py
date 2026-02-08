"""
Phase 4 — Step 4.1: Slot Map Execution.
After every (simulated or real) user message: update state from extractions + refusal handling.
Slot ownership: source, confidence, timestamp. Nothing overwritten blindly.
"""

import re
from datetime import datetime
from typing import Any

from src.nlp.entities import extract_entities
from src.state.models import ConversationStage, ConversationState, SlotStatus, SlotValue
from src.state.slot_registry import get_optional_slots, get_refusal_phrases, get_required_slots

# Entity key → slot name (MVP frozen slots)
ENTITY_TO_SLOT = {
    "content_type": "project_type",
    "style": "animation_type",
    "duration_minutes": "approx_duration",
    "platform": "usage",
}

# Simple patterns for name, country, budget, timeline (single message)
NAME_PATTERNS = [
    re.compile(r"(?:my name is|i'm|i am|this is|call me)\s+([A-Za-z][A-Za-z\s\-']{1,48})\b", re.I),
    re.compile(r"\b(?:name|contact)\s*[:\s]+\s*([A-Za-z][A-Za-z\s\-']{1,48})\b", re.I),
]
COUNTRY_PATTERNS = [
    re.compile(r"(?:from|based in|in|we're in|located in)\s+([A-Za-z][A-Za-z\s\-']{1,48})\b", re.I),
    re.compile(r"\b(?:country|region)\s*[:\s]+\s*([A-Za-z][A-Za-z\s\-']{1,48})\b", re.I),
]
BUDGET_PATTERNS = [
    re.compile(r"budget\s*(?:is|of)?\s*[:\s]*([0-9,]+\s*(?:k|K|USD|usd|\$|dollars?)?)", re.I),
    re.compile(r"(?:around|about)\s+([0-9,]+\s*(?:k|K|USD|usd|\$|dollars?))", re.I),
]
TIMELINE_PATTERNS = [
    re.compile(r"(?:by|before|deadline|need it by)\s+([A-Za-z0-9\s,]+?)(?:\.|$|\s+and)", re.I),
    re.compile(r"timeline\s*[:\s]+\s*([A-Za-z0-9\s,]+?)(?:\.|$)", re.I),
]


def _extract_slot_from_text(text: str, patterns: list) -> str | None:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1).strip()[:200]
    return None


def extract_slot_values_from_message(text: str, source_id: str, confidence_base: float = 0.8) -> dict[str, SlotValue]:
    """
    From one message: run entity extraction + simple name/country/budget/timeline.
    Returns dict slot_name → SlotValue (for slots that got a value). Ownership: source, confidence, timestamp.
    """
    now = datetime.utcnow().isoformat() + "Z"
    out: dict[str, SlotValue] = {}
    entities = extract_entities(text)

    for entity_key, slot_name in ENTITY_TO_SLOT.items():
        val = entities.get(entity_key)
        if val is not None:
            sv = SlotValue(
                value=val,
                status=SlotStatus.FILLED,
                confidence=confidence_base,
                source=source_id,
                timestamp=now,
            )
            out[slot_name] = sv
            if slot_name == "approx_duration":
                out["duration"] = sv

    name = _extract_slot_from_text(text, NAME_PATTERNS)
    if name:
        sv = SlotValue(value=name, status=SlotStatus.FILLED, confidence=confidence_base, source=source_id, timestamp=now)
        out["name"] = out["caller_name"] = sv
    country = _extract_slot_from_text(text, COUNTRY_PATTERNS)
    if country:
        out["country_location"] = SlotValue(value=country, status=SlotStatus.FILLED, confidence=confidence_base, source=source_id, timestamp=now)
    budget = _extract_slot_from_text(text, BUDGET_PATTERNS)
    if budget:
        out["budget_or_range"] = SlotValue(value=budget, status=SlotStatus.FILLED, confidence=confidence_base, source=source_id, timestamp=now)
    timeline = _extract_slot_from_text(text, TIMELINE_PATTERNS)
    if timeline:
        out["deadline"] = SlotValue(value=timeline, status=SlotStatus.FILLED, confidence=confidence_base, source=source_id, timestamp=now)

    return out


def _is_refusal(message: str, slot_name: str, intent: str | None) -> bool:
    phrases = get_refusal_phrases(slot_name, intent)
    msg_lower = message.lower().strip()
    if len(msg_lower) < 3:
        return False
    for p in phrases:
        if p.lower() in msg_lower:
            return True
    if msg_lower in ("no", "nope", "skip", "pass", "rather not"):
        return True
    return False


def update_state_from_message(
    state: ConversationState,
    message_text: str,
    source_id: str,
    intent: str | None,
    *,
    is_user_turn: bool = True,
) -> ConversationState:
    """
    Slot map execution: update state from one message.
    - Run extraction, merge into slots (only if new value and confidence >= existing).
    - If is_user_turn and message is refusal for last_question_asked → that slot unavailable.
    - Recompute slot status (filled/missing/unavailable) vs required/optional for intent.
    Nothing deleted; no blind overwrite.
    """
    now = datetime.utcnow().isoformat() + "Z"
    intent = intent or state.intent or "new_project_sales"
    required = set(get_required_slots(intent))
    optional = set(get_optional_slots(intent))
    all_slots = required | optional

    new_slots = dict(state.slots)

    # Refusal: mark last_question_asked slot as refused
    if is_user_turn and state.last_question_asked and _is_refusal(message_text, state.last_question_asked, intent):
        slot = new_slots.get(state.last_question_asked) or SlotValue()
        new_slots[state.last_question_asked] = SlotValue(
            value=slot.value,
            status=SlotStatus.REFUSED,
            confidence=slot.confidence,
            source=slot.source,
            timestamp=now,
        )

    # New extractions from this message
    from_message = extract_slot_values_from_message(message_text, source_id)
    for slot_name, new_sv in from_message.items():
        if slot_name not in all_slots:
            continue
        existing = new_slots.get(slot_name)
        if existing and existing.status in (SlotStatus.UNAVAILABLE, SlotStatus.REFUSED):
            continue
        if existing and existing.value is not None and new_sv.confidence <= existing.confidence:
            continue
        new_slots[slot_name] = new_sv

    # Ensure all required/optional have an entry; set status
    for name in all_slots:
        sv = new_slots.get(name) or SlotValue()
        if sv.status in (SlotStatus.UNAVAILABLE, SlotStatus.REFUSED):
            continue
        if sv.value is not None and sv.value != "":
            new_slots[name] = SlotValue(
                value=sv.value,
                status=SlotStatus.FILLED,
                confidence=sv.confidence,
                source=sv.source,
                timestamp=sv.timestamp,
            )
        else:
            new_slots[name] = SlotValue(status=SlotStatus.MISSING)

    # Stage
    required_filled = all(
        (new_slots.get(r) or SlotValue()).status == SlotStatus.FILLED for r in required
    )
    stage = (
        ConversationStage.MINIMUM_COMPLETENESS_REACHED
        if required_filled
        else ConversationStage.SLOT_FILLING
    )

    return ConversationState(
        intent=intent,
        slots=new_slots,
        last_question_asked=state.last_question_asked,
        last_question_at=state.last_question_at,
        stage=stage,
        updated_at=now,
    )


def recompute_slot_status(state: ConversationState, intent: str) -> ConversationState:
    """Recompute status for all slots from required/optional. Keep values and ownership."""
    required = set(get_required_slots(intent))
    optional = set(get_optional_slots(intent))
    all_slots = required | optional
    new_slots = dict(state.slots)
    for name in all_slots:
        sv = new_slots.get(name) or SlotValue()
        if sv.status in (SlotStatus.UNAVAILABLE, SlotStatus.REFUSED):
            continue
        if sv.value is not None and sv.value != "":
            new_slots[name] = SlotValue(
                value=sv.value,
                status=SlotStatus.FILLED,
                confidence=sv.confidence,
                source=sv.source,
                timestamp=sv.timestamp,
            )
        else:
            new_slots[name] = SlotValue(status=SlotStatus.MISSING)
    required_filled = all((new_slots.get(r) or SlotValue()).status == SlotStatus.FILLED for r in required)
    stage = (
        ConversationStage.MINIMUM_COMPLETENESS_REACHED
        if required_filled
        else ConversationStage.SLOT_FILLING
    )
    return state.model_copy(update={"slots": new_slots, "stage": stage, "intent": intent})
