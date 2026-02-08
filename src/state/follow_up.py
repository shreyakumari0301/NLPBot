"""
Phase 4 — Step 4.2: Follow-Up Strategy Execution.
Priority engine: one question at a time. Question templates, refusal handled. Stop conditions.
"""

from datetime import datetime

from src.state.models import ConversationStage, ConversationState, SlotStatus
from src.state.slot_registry import (
    FOLLOW_UP_PRIORITY,
    get_optional_slots,
    get_question_templates,
    get_required_slots,
)

# Don't re-ask same slot for at least this many "turns" (we use state.last_question_asked only; re-ask only if we have a different slot to try first)
RECENT_ASK_WINDOW = 1  # treat as "recent" if we just asked this slot

# Closure phrases: user wants to end
CLOSURE_PHRASES = (
    "that's all",
    "that is all",
    "goodbye",
    "good bye",
    "thanks that's it",
    "no more questions",
    "end conversation",
    "stop",
    "we're done",
    "we are done",
)


def user_wants_closure(message: str) -> bool:
    msg = (message or "").strip().lower()
    return any(p in msg for p in CLOSURE_PHRASES) or msg in ("no", "nope", "that's it")


def should_stop_asking(state: ConversationState) -> bool:
    """
    Stop when: all required filled, or user asked for closure (handled by caller with last message),
    or stage is closure. Timeout/handoff can be added later.
    """
    if state.stage == ConversationStage.CONVERSATION_CLOSURE:
        return True
    if state.stage == ConversationStage.MINIMUM_COMPLETENESS_REACHED:
        return True
    intent = state.intent or "new_project_sales"
    required = get_required_slots(intent)
    for r in required:
        sv = state.get_slot(r)
        if sv.status != SlotStatus.FILLED and sv.status != SlotStatus.UNAVAILABLE:
            return False
    return True


def get_next_question(
    state: ConversationState,
    *,
    turn_index: int = 0,
    last_user_message: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Returns (question_text, slot_name) or (None, None) if no question to ask.
    Only one question; chosen by priority. Skips recently-asked slot (avoid repeat).
    """
    if should_stop_asking(state):
        return None, None
    if last_user_message and user_wants_closure(last_user_message):
        return None, None

    intent = state.intent or "new_project_sales"
    required = get_required_slots(intent)
    optional = get_optional_slots(intent)
    # Priority: required first (in FOLLOW_UP_PRIORITY order), then optional
    ordered = [s for s in FOLLOW_UP_PRIORITY if s in required] + [
        s for s in FOLLOW_UP_PRIORITY if s in optional and s not in required
    ]

    for slot_name in ordered:
        sv = state.get_slot(slot_name)
        if sv.status != SlotStatus.MISSING:
            continue
        if state.last_question_asked == slot_name:
            continue
        templates = get_question_templates(slot_name, intent)
        if not templates:
            continue
        idx = turn_index % len(templates)
        question = templates[idx]
        return question, slot_name
    return None, None


def apply_question_asked(state: ConversationState, slot_name: str) -> ConversationState:
    """After system asks a question, update state so we don't repeat immediately."""
    now = datetime.utcnow().isoformat() + "Z"
    return state.model_copy(
        update={
            "last_question_asked": slot_name,
            "last_question_at": now,
            "updated_at": now,
        }
    )
