"""Request/response shapes for the Channel Ingestion API."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas import ChannelSource, SpeakerTurn


class IncomingTurn(BaseModel):
    speaker_id: str
    text: str
    timestamp: datetime | None = None


class IncomingChatPayload(BaseModel):
    """Text chat: client sends turns (or full transcript)."""

    channel: ChannelSource = ChannelSource.CHAT
    turns: list[IncomingTurn] = Field(..., min_length=1)
    conversation_id: str | None = None  # optional; server generates if missing


class IncomingVoicePayload(BaseModel):
    """Voice/call: client sends audio URL or reference; transcription runs async."""

    channel: ChannelSource = ChannelSource.VOICE
    audio_url: str | None = None
    transcript: str | None = None  # pre-transcribed text if already available
    conversation_id: str | None = None


class IngestionResponse(BaseModel):
    conversation_id: str
    status: str = "registered"
    message: str = "Conversation ready for NLP"
