"""Text Normalization Worker: raw text → clean text for NLP."""

import re
from unicodedata import normalize as unicode_normalize

from src.schemas import SpeakerTurn


def normalize_text(text: str) -> str:
    """
    Normalize for English NLP: NFC, collapse whitespace, strip.
    No fancy personalization; keep predictable.
    """
    if not text:
        return ""
    t = unicode_normalize("NFC", text)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def normalize_turns(turns: list[SpeakerTurn]) -> tuple[str, str, list[SpeakerTurn]]:
    """
    From speaker turns produce: raw_transcript, clean_text, normalized_turns.
    Raw = concatenated original; clean = normalized concatenation.
    """
    raw_parts = [t.text for t in turns]
    raw_transcript = "\n".join(raw_parts)
    clean_parts = [normalize_text(t.text) for t in turns]
    clean_text = "\n".join(p for p in clean_parts if p)
    normalized_turns = [
        SpeakerTurn(
            speaker_id=t.speaker_id,
            text=normalize_text(t.text),
            timestamp=t.timestamp,
        )
        for t in turns
    ]
    return raw_transcript, clean_text, normalized_turns
