"""Transcription Worker: voice → text. Stub for Phase 2 (post-conversation, text-first)."""

from src.schemas import SpeakerTurn


def transcribe_audio(audio_url: str) -> list[SpeakerTurn]:
    """
    Placeholder: in production this would call a speech-to-text API.
    Returns speaker turns; for now returns a single turn with a placeholder.
    """
    # Stub: no actual audio fetch. Real impl would use Whisper, AssemblyAI, etc.
    return [
        SpeakerTurn(
            speaker_id="unknown",
            text="[Transcription not implemented: audio_url=" + audio_url[:80] + "]",
            timestamp=None,
        )
    ]


def transcribe_from_raw_text(transcript: str) -> list[SpeakerTurn]:
    """Use when client sends pre-transcribed text (e.g. from their own STT)."""
    if not (transcript or transcript.strip()):
        return []
    return [
        SpeakerTurn(speaker_id="speaker_1", text=transcript.strip(), timestamp=None)
    ]
