"""
Phase 4 — Conversation State & Slot value models.
State is recalculated after every user message.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SlotStatus(str, Enum):
    FILLED = "filled"
    MISSING = "missing"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class ConversationStage(str, Enum):
    INTENT_DISCOVERY = "intent_discovery"
    SLOT_FILLING = "slot_filling"
    MINIMUM_COMPLETENESS_REACHED = "minimum_completeness_reached"
    OPTIONAL_ENRICHMENT = "optional_enrichment"
    CONVERSATION_CLOSURE = "conversation_closure"


class SlotValue(BaseModel):
    """Per-slot: value, status, confidence, source (which message), timestamp."""

    value: Any = None
    status: SlotStatus = SlotStatus.MISSING
    confidence: float = 0.0
    source: str | None = None  # e.g. "turn_2", "message_3"
    timestamp: str | None = None  # ISO when filled/updated


class ConversationState(BaseModel):
    """
    Per-conversation state snapshot. Updated continuously.
    """

    intent: str | None = None
    slots: dict[str, SlotValue] = Field(default_factory=dict)
    last_question_asked: str | None = None  # slot name
    last_question_at: str | None = None  # ISO timestamp; for "asked recently" check
    stage: ConversationStage = ConversationStage.INTENT_DISCOVERY
    updated_at: str | None = None  # ISO

    def get_slot(self, name: str) -> SlotValue:
        if name in self.slots:
            return self.slots[name]
        return SlotValue(status=SlotStatus.MISSING)
