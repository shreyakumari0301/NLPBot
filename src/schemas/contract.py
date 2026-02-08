"""
Phase 1: Unit of Truth — One conversation output contract.
Every later improvement (NLP, scoring, extraction) plugs into this output.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChannelSource(str, Enum):
    CHAT = "chat"
    VOICE = "voice"


class CompletenessStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETE = "complete"
    UNKNOWN = "unknown"


# --- Per-turn (for registry / intake) ---


class SpeakerTurn(BaseModel):
    speaker_id: str
    text: str
    timestamp: datetime | None = None


# --- Full conversation output (the contract) ---


class ConversationMetadata(BaseModel):
    conversation_id: str
    channel_source: ChannelSource
    started_at: datetime | None = None
    ended_at: datetime | None = None
    language: str = "en"
    geo_metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationOutput(BaseModel):
    """One conversation → this structure. Canonical output for analytics & NLP."""

    conversation_id: str
    raw_transcript: str
    primary_intent: str | None = None
    secondary_tags: list[str] = Field(default_factory=list)
    extracted_structured_fields: dict[str, Any] = Field(default_factory=dict)
    completeness_status: CompletenessStatus = CompletenessStatus.UNKNOWN
    auto_generated_summary: str | None = None
    lead_score: float | None = None
    conversation_metadata: ConversationMetadata

    # Normalized/clean text (from intake pipeline)
    clean_text: str | None = None

    # Preserved for reprocessing
    speaker_turns: list[SpeakerTurn] = Field(default_factory=list)
