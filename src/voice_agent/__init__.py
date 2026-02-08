"""
Full-duplex voice agent: STT (faster-whisper), VAD (webrtcvad), TTS (optional).
Local, call-center style with interrupt support. All imports are lazy so the app
runs even if these deps are not installed.
"""

__all__ = [
    "transcribe_audio",
    "is_speech_frame",
    "voice_activity_frames",
    "text_to_speech_bytes",
]


def __getattr__(name):
    if name == "transcribe_audio":
        from src.voice_agent.stt import transcribe_audio
        return transcribe_audio
    if name == "is_speech_frame":
        from src.voice_agent.vad import is_speech_frame
        return is_speech_frame
    if name == "voice_activity_frames":
        from src.voice_agent.vad import voice_activity_frames
        return voice_activity_frames
    if name == "text_to_speech_bytes":
        from src.voice_agent.tts import text_to_speech_bytes
        return text_to_speech_bytes
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
