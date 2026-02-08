"""
Phase 4 — State pipeline: build/update conversation state from conversation or new message.
Replay turn-by-turn for accuracy (refusal, last_question_asked). Recalculates after every user message.
"""

from src.state.models import ConversationState, ConversationStage
from src.state.slot_filling import update_state_from_message
from src.state.slot_registry import get_required_slots


def initial_state(intent: str | None) -> ConversationState:
    """Fresh state for a conversation. Intent may be updated later."""
    return ConversationState(
        intent=intent or "new_project_sales",
        slots={},
        stage=ConversationStage.INTENT_DISCOVERY,
    )


def build_state_from_conversation(
    full_text: str,
    speaker_turns: list[tuple[str, str]],
    intent: str,
) -> ConversationState:
    """
    Replay conversation turn-by-turn: for each user turn, run slot map execution.
    Assumes speaker_turns are (speaker_id, text); treats non-'agent' as user for refusal/flow.
    """
    state = initial_state(intent)
    for i, (speaker_id, text) in enumerate(speaker_turns):
        if not text or not text.strip():
            continue
        source_id = f"turn_{i}"
        is_user = speaker_id.lower() not in ("agent", "bot", "system")
        state = update_state_from_message(
            state,
            text.strip(),
            source_id,
            intent,
            is_user_turn=is_user,
        )
    return state


def build_state_from_full_text(full_text: str, intent: str) -> ConversationState:
    """
    Single-shot: treat full conversation as one message. No per-turn refusal.
    Use when turn-by-turn replay is not available.
    """
    state = initial_state(intent)
    state = update_state_from_message(
        state,
        full_text,
        "full_transcript",
        intent,
        is_user_turn=True,
    )
    return state
