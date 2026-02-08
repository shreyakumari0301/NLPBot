"""
Live conversation API — localhost. Greet first, then each user message returns bot reply.
Full-duplex: POST /live/audio for STT → turn → optional TTS; interrupt = stop playback and send next.
"""

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from src.live.session import get_session, start_session, turn

router = APIRouter(prefix="/live", tags=["live"])


@router.post("/start")
def live_start():
    """Start a live session. Returns session_id and greeting: 'Hello sir, how may I help you?'"""
    session_id, greeting = start_session()
    return {"session_id": session_id, "bot_reply": greeting}


@router.post("/message")
def live_message(body: dict):
    """
    Send user message, get bot reply. Body: { "session_id": "...", "user_message": "..." }.
    Bot checks required slots, answers services queries, notes complaints, remembers context.
    """
    session_id = body.get("session_id")
    user_message = (body.get("user_message") or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    if not user_message:
        raise HTTPException(status_code=400, detail="user_message required")
    bot_reply, state, intent = turn(session_id, user_message)
    return {
        "session_id": session_id,
        "bot_reply": bot_reply,
        "intent": intent,
        "state": state.model_dump(mode="json"),
    }


@router.get("/session/{session_id}")
def live_get_session(session_id: str):
    """Get current session state and history (for debugging)."""
    data = get_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "state": data["state"].model_dump(mode="json"),
        "history": data["history"],
        "turn_index": data["turn_index"],
    }


# ---------- Full-duplex voice agent: STT → turn → optional TTS ----------

def _audio_bytes_from_upload(file: UploadFile) -> bytes:
    """Read upload as raw bytes (WebM from MediaRecorder, WAV, or raw PCM)."""
    body = file.file.read()
    return body or b""


@router.post("/audio")
async def live_audio(
    session_id: str = Form(...),
    audio: UploadFile = File(..., description="Raw 16 kHz mono PCM or WAV"),
    return_tts: Optional[str] = Form("false"),
):
    """
    Voice in: upload audio → STT (faster-whisper) → turn(session, transcript) → bot reply.
    Optionally return TTS audio (base64) when return_tts=true so client can play local female voice.
    Interrupt: client stops TTS playback and sends next audio; no extra API needed.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    audio_bytes = _audio_bytes_from_upload(audio)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data")
    transcript = ""
    try:
        from src.voice_agent.stt import transcribe_audio_file

        transcript = transcribe_audio_file(audio_bytes, sample_rate=16000)
    except Exception:
        try:
            from src.voice_agent.stt import transcribe_audio

            transcript = transcribe_audio(audio_bytes, sample_rate=16000)
        except Exception:
            pass
    if not transcript.strip():
        return {
            "session_id": session_id,
            "transcript": "",
            "bot_reply": "I didn't catch that. Could you say it again?",
            "tts_audio_base64": None,
        }
    bot_reply, state, intent = turn(session_id, transcript)
    tts_b64 = None
    if str(return_tts).lower() in ("true", "1", "yes"):
        try:
            from src.voice_agent import text_to_speech_bytes

            wav = text_to_speech_bytes(bot_reply)
            if wav:
                tts_b64 = base64.b64encode(wav).decode("ascii")
        except Exception:
            pass
    return {
        "session_id": session_id,
        "transcript": transcript,
        "bot_reply": bot_reply,
        "intent": intent,
        "state": state.model_dump(mode="json"),
        "tts_audio_base64": tts_b64,
    }


@router.get("/tts")
def live_tts(text: str = ""):
    """Return WAV audio for the given text (Mira voice). For streaming/interrupt, call with sentence chunks."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")
    try:
        from src.voice_agent import text_to_speech_bytes

        wav = text_to_speech_bytes(text)
    except Exception:
        wav = None
    if not wav:
        raise HTTPException(status_code=503, detail="TTS not available (install pyttsx3 or set USE_COQUI_TTS)")
    return Response(content=wav, media_type="audio/wav")
