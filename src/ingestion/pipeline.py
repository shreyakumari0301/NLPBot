"""
Intake pipeline: Incoming → Channel Ingestion API → Registry → (Voice?) Transcription → Normalization → Stored.
"""

from src.ingestion.payloads import IncomingChatPayload, IncomingVoicePayload
from src.registry.store import (
    generate_conversation_id,
    register_conversation,
)
from src.schemas import ChannelSource, SpeakerTurn
from src.workers.normalization import normalize_turns
from src.workers.transcription import transcribe_audio, transcribe_from_raw_text


def _incoming_to_turns(chat: IncomingChatPayload) -> list[SpeakerTurn]:
    return [
        SpeakerTurn(
            speaker_id=t.speaker_id,
            text=t.text,
            timestamp=t.timestamp,
        )
        for t in chat.turns
    ]


def process_chat(payload: IncomingChatPayload) -> str:
    """Chat path: turns already text → normalize → store. Returns conversation_id."""
    cid = payload.conversation_id or generate_conversation_id()
    turns = _incoming_to_turns(payload)
    raw_transcript, clean_text, normalized_turns = normalize_turns(turns)
    started = turns[0].timestamp.isoformat() if turns and turns[0].timestamp else None
    ended = turns[-1].timestamp.isoformat() if turns and turns[-1].timestamp else None
    register_conversation(
        conversation_id=cid,
        channel_source=ChannelSource.CHAT,
        speaker_turns=normalized_turns,
        raw_transcript=raw_transcript,
        clean_text=clean_text,
        started_at=started,
        ended_at=ended,
    )
    return cid


def process_voice(payload: IncomingVoicePayload) -> str:
    """Voice path: audio or pre-transcript → transcribe (stub) → normalize → store."""
    cid = payload.conversation_id or generate_conversation_id()
    if payload.transcript:
        turns = transcribe_from_raw_text(payload.transcript)
    elif payload.audio_url:
        turns = transcribe_audio(payload.audio_url)
    else:
        turns = [
            SpeakerTurn(speaker_id="unknown", text="[No transcript or audio_url]", timestamp=None)
        ]
    raw_transcript, clean_text, normalized_turns = normalize_turns(turns)
    register_conversation(
        conversation_id=cid,
        channel_source=ChannelSource.VOICE,
        speaker_turns=normalized_turns,
        raw_transcript=raw_transcript,
        clean_text=clean_text,
        started_at=None,
        ended_at=None,
    )
    return cid
