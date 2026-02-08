"""
Speech-to-Text via faster-whisper (local). Stream-friendly; use for live transcription.
Expects 16 kHz mono PCM or raw bytes (converted to float32).
"""

import io
import struct
from typing import Optional

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
        )
        return _model
    except Exception:
        return None


def transcribe_audio(
    audio_bytes: bytes,
    sample_rate: int = 16000,
    language: Optional[str] = "en",
) -> str:
    """
    Transcribe raw audio bytes (16-bit PCM mono at sample_rate) to text.
    Returns empty string if STT not available or no speech.
    """
    model = _get_model()
    if not model:
        return ""
    try:
        # Convert 16-bit PCM to float32 [-1, 1]
        num_samples = len(audio_bytes) // 2
        fmt = "<%dh" % num_samples
        samples = struct.unpack(fmt, audio_bytes[: num_samples * 2])
        import numpy as np

        audio_f32 = np.array(samples, dtype=np.float32) / 32768.0
        segments, _ = model.transcribe(
            audio_f32,
            language=language,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=200),
        )
        return " ".join(s.text.strip() for s in segments if s.text).strip()
    except Exception:
        return ""


def transcribe_audio_file(
    path_or_bytes: str | bytes,
    sample_rate: int = 16000,
    language: Optional[str] = "en",
) -> str:
    """
    Transcribe from file path or bytes (WAV/WebM/MP3 etc. via decode_audio).
    Use for browser uploads (e.g. MediaRecorder WebM).
    """
    model = _get_model()
    if not model:
        return ""
    try:
        from faster_whisper import decode_audio

        if isinstance(path_or_bytes, bytes):
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(path_or_bytes)
                path = f.name
            try:
                audio_f32 = decode_audio(path, sampling_rate=sample_rate)
            finally:
                import os

                try:
                    os.unlink(path)
                except Exception:
                    pass
        else:
            audio_f32 = decode_audio(path_or_bytes, sampling_rate=sample_rate)
        segments, _ = model.transcribe(
            audio_f32,
            language=language,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=200),
        )
        return " ".join(s.text.strip() for s in segments if s.text).strip()
    except Exception:
        return ""
