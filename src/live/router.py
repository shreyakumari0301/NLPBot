"""
Live conversation API — localhost. Greet first, then each user message returns bot reply.
Processes live: intent, slot capture, FAQ for services query, complaints noted.
"""

from fastapi import APIRouter, HTTPException

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
