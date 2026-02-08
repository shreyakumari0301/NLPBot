"""
Voice Activity Detection via webrtcvad. 16-bit PCM, 8/16/32/48 kHz, 10/20/30 ms frames.
Used to detect when user starts speaking (interrupt) and when they stop (finalize transcript).
"""

import struct
from typing import Iterator

_vad = None


def _get_vad(aggressiveness: int = 2):
    global _vad
    if _vad is not None:
        return _vad
    try:
        import webrtcvad

        _vad = webrtcvad.Vad(aggressiveness)
        return _vad
    except Exception:
        return None


def is_speech_frame(frame_bytes: bytes, sample_rate: int = 16000) -> bool:
    """
    Return True if this frame contains speech. Frame must be 10, 20, or 30 ms of 16-bit PCM.
    """
    vad = _get_vad()
    if not vad:
        return False
    if sample_rate not in (8000, 16000, 32000, 48000):
        sample_rate = 16000
    duration_ms = len(frame_bytes) // (2 * sample_rate // 1000)
    if duration_ms not in (10, 20, 30):
        return False
    try:
        return vad.is_speech(frame_bytes, sample_rate)
    except Exception:
        return False


def voice_activity_frames(
    audio_bytes: bytes,
    sample_rate: int = 16000,
    frame_duration_ms: int = 30,
) -> Iterator[tuple[bytes, bool]]:
    """
    Yield (frame_bytes, is_speech) for each frame. Use to detect start/end of speech.
    """
    vad = _get_vad()
    if not vad or sample_rate not in (8000, 16000, 32000, 48000):
        return
    if frame_duration_ms not in (10, 20, 30):
        frame_duration_ms = 30
    frame_len = sample_rate * frame_duration_ms // 1000 * 2
    for i in range(0, len(audio_bytes) - frame_len + 1, frame_len):
        frame = audio_bytes[i : i + frame_len]
        try:
            yield frame, vad.is_speech(frame, sample_rate)
        except Exception:
            yield frame, False
