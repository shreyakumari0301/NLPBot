"""
Text-to-Speech for Mira: local female voice. Coqui XTTS or pyttsx3; None = use browser TTS.
"""

import io
import os
import tempfile
from typing import Optional

_tts_engine = None


def _get_tts():
    global _tts_engine
    if _tts_engine is not None:
        return _tts_engine
    if os.environ.get("USE_COQUI_TTS", "").lower() in ("1", "true", "yes"):
        try:
            from TTS.api import TTS

            model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            model.to("cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu")
            _tts_engine = ("coqui", model)
            return _tts_engine
        except Exception:
            pass
    try:
        import pyttsx3

        eng = pyttsx3.init()
        for v in eng.getProperty("voices"):
            if "female" in (v.name or "").lower() or "zira" in (v.name or "").lower():
                eng.setProperty("voice", v.id)
                break
        _tts_engine = ("pyttsx3", eng)
        return _tts_engine
    except Exception:
        pass
    _tts_engine = ("none", None)
    return _tts_engine


def text_to_speech_bytes(text: str, sample_rate: int = 22050) -> Optional[bytes]:
    """Return WAV bytes for text, or None (caller uses browser TTS)."""
    if not (text or "").strip():
        return None
    kind, engine = _get_tts()
    if kind == "none" or engine is None:
        return None
    try:
        if kind == "coqui":
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            engine.tts_to_file(text=text.strip(), file_path=path, language="en")
            with open(path, "rb") as f:
                out = f.read()
            try:
                os.unlink(path)
            except Exception:
                pass
            return out
        if kind == "pyttsx3":
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            engine.save_to_file(text.strip(), path)
            engine.runAndWait()
            with open(path, "rb") as f:
                out = f.read()
            try:
                os.unlink(path)
            except Exception:
                pass
            return out
    except Exception:
        return None
    return None
