"""Channel Ingestion API: receive chat or voice, run intake pipeline, return conversation_id."""

import json

from fastapi import APIRouter, HTTPException

from src.ingestion.payloads import (
    IncomingChatPayload,
    IncomingVoicePayload,
    IngestionResponse,
)
from src.ingestion.pipeline import process_chat, process_voice
from src.nlp.pipeline import run_and_persist
from src.qualification import completeness_summary, lead_score_summary
from src.qualification.completeness import CompletenessStatus
from src.registry import (
    append_human_action,
    append_lead,
    append_processing_run,
    get_conversation,
    get_state_json,
    save_state_json,
    update_completeness_status,
    update_lead_score,
    update_nlp_results,
)
from src.schemas import ConversationOutput
from src.state import (
    build_state_from_conversation,
    build_state_from_full_text,
    get_next_question,
    update_state_from_message,
)
from src.state.models import ConversationState, ConversationStage

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/chat", response_model=IngestionResponse)
def ingest_chat(payload: IncomingChatPayload) -> IngestionResponse:
    """Incoming chat → Conversation Registry → Text Normalization → Raw + Clean stored."""
    cid = process_chat(payload)
    return IngestionResponse(
        conversation_id=cid,
        status="registered",
        message="Conversation ready for NLP",
    )


@router.post("/voice", response_model=IngestionResponse)
def ingest_voice(payload: IncomingVoicePayload) -> IngestionResponse:
    """Incoming call/voice → (Transcription Worker) → Text Normalization → Raw + Clean stored."""
    cid = process_voice(payload)
    return IngestionResponse(
        conversation_id=cid,
        status="registered",
        message="Conversation ready for NLP",
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOutput)
def get_stored_conversation(conversation_id: str) -> ConversationOutput:
    """Retrieve stored conversation (raw + clean text, metadata) for NLP/analytics."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations/{conversation_id}/process")
def process_conversation_nlp(conversation_id: str):
    """
    Run Phase 3 NLP pipeline: preprocess → intent (tentative + final) → entity extraction.
    Persists primary intent, secondary tags, extracted fields to the conversation.
    Re-runnable.
    """
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    turn_texts = [t.text for t in conv.speaker_turns]
    clean = conv.clean_text or conv.raw_transcript or ""
    result = run_and_persist(
        conversation_id,
        clean,
        turn_texts,
        update_nlp_results,
    )
    return {
        "conversation_id": conversation_id,
        "status": "processed",
        "language": result["language"],
        "tentative_intent": result["tentative_intent"],
        "final_intent": result["final_intent"],
        "extracted_entities": result["extracted_entities"],
    }


def _state_to_response(state: ConversationState) -> dict:
    return state.model_dump(mode="json")


@router.get("/conversations/{conversation_id}/state")
def get_conversation_state(conversation_id: str):
    """Phase 4: Get conversation state (slots, intent, stage)."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    raw = get_state_json(conversation_id)
    if not raw:
        return {"conversation_id": conversation_id, "state": None, "message": "State not built yet. POST to /state to build."}
    state = ConversationState.model_validate(json.loads(raw))
    return {"conversation_id": conversation_id, "state": _state_to_response(state)}


@router.get("/conversations/{conversation_id}/qualification")
def get_conversation_qualification(conversation_id: str):
    """Phase 5: Get completeness (%, missing, status) and lead score (score, band, breakdown)."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    raw = get_state_json(conversation_id)
    if not raw:
        return {
            "conversation_id": conversation_id,
            "completeness": None,
            "lead": None,
            "message": "State not built yet. POST to /state to build.",
        }
    state = ConversationState.model_validate(json.loads(raw))
    comp = completeness_summary(state)
    clean = conv.clean_text or conv.raw_transcript or ""
    turn_count = len(conv.speaker_turns)
    lead = lead_score_summary(state, num_turns=turn_count, full_text=clean)
    return {
        "conversation_id": conversation_id,
        "completeness": comp,
        "lead": lead,
    }


@router.post("/conversations/{conversation_id}/state")
def build_and_save_state(conversation_id: str):
    """
    Phase 4: Build state from conversation (turn-by-turn slot filling), save, return state + next question.
    Run after NLP process so primary_intent is set.
    """
    try:
        conv = get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        intent = conv.primary_intent or "new_project_sales"
        turns = [(t.speaker_id, t.text) for t in conv.speaker_turns]
        clean = conv.clean_text or conv.raw_transcript or ""
        if turns:
            state = build_state_from_conversation(clean, turns, intent)
        else:
            state = build_state_from_full_text(clean, intent)
        state_json_str = state.model_dump_json()
        ok = save_state_json(conversation_id, state_json_str)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to save state (conversation not found or DB error)")
        if state.stage == ConversationStage.MINIMUM_COMPLETENESS_REACHED:
            update_completeness_status(conversation_id, "complete")
        # Phase 5 & 6: completeness, lead score, append-only runs/leads
        comp = completeness_summary(state)
        clean = conv.clean_text or conv.raw_transcript or ""
        lead = lead_score_summary(state, num_turns=len(turns), full_text=clean)
        label = comp["status"]
        status_for_db = label  # complete | actionable | incomplete | info_only
        update_completeness_status(conversation_id, status_for_db)
        update_lead_score(conversation_id, lead["lead_score"], lead["lead_band"])
        append_processing_run(
            conversation_id,
            state_json=state_json_str,
            completeness_pct=comp["completeness_pct"],
            mandatory_missing_json=json.dumps(comp["mandatory_fields_missing"]),
            completeness_label=label,
            lead_score=lead["lead_score"],
            lead_band=lead["lead_band"],
            lead_breakdown_json=json.dumps(lead["breakdown"]),
        )
        if label in (CompletenessStatus.COMPLETE.value, CompletenessStatus.ACTIONABLE.value):
            slots_ser = json.dumps({k: v.model_dump(mode="json") for k, v in state.slots.items()})
            append_lead(
                conversation_id,
                intent=state.intent,
                slots_json=slots_ser,
                completeness_pct=comp["completeness_pct"],
                completeness_label=label,
                lead_score=lead["lead_score"],
                lead_band=lead["lead_band"],
                lead_breakdown_json=json.dumps(lead["breakdown"]),
            )
        question, slot = get_next_question(state, turn_index=len(turns))
        return {
            "conversation_id": conversation_id,
            "state": _state_to_response(state),
            "completeness": comp,
            "lead": lead,
            "next_question": question,
            "next_question_slot": slot,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"State build failed: {type(e).__name__}: {e}")


@router.post("/conversations/{conversation_id}/state/message")
def append_message_and_update_state(conversation_id: str, body: dict):
    """
    Phase 4: Append a user message, update state (slot map execution), save. Returns new state + next question.
    Body: { "text": "...", "speaker_id": "user" }
    """
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    intent = conv.primary_intent or "new_project_sales"
    raw = get_state_json(conversation_id)
    if raw:
        state = ConversationState.model_validate(json.loads(raw))
    else:
        state = build_state_from_full_text(conv.clean_text or conv.raw_transcript or "", intent)
    turn_index = len(conv.speaker_turns) + 1
    state = update_state_from_message(state, text, f"turn_{turn_index}", intent, is_user_turn=True)
    save_state_json(conversation_id, state.model_dump_json())
    question, slot = get_next_question(state, turn_index=turn_index, last_user_message=text)
    return {
        "conversation_id": conversation_id,
        "state": _state_to_response(state),
        "next_question": question,
        "next_question_slot": slot,
    }


@router.post("/conversations/{conversation_id}/human-takeover")
def record_human_takeover(conversation_id: str, body: dict):
    """
    Phase 8: Record that human took over. Body: { "trigger_reason": "low_confidence"|"frustration_detected"|"complaint_intent" }.
    Append-only gold data.
    """
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    reason = body.get("trigger_reason") or "manual"
    aid = append_human_action(conversation_id, trigger_reason=reason)
    return {"conversation_id": conversation_id, "action_id": aid, "trigger_reason": reason}


@router.post("/conversations/{conversation_id}/human-actions")
def record_human_actions(conversation_id: str, body: dict):
    """
    Phase 8: Human corrections — correct intent, fill missing fields, close or convert lead.
    Body: { "corrected_intent": "...", "filled_slots": {...}, "action": "close"|"convert"|"none", "notes": "..." }.
    Stored as gold data; optionally updates conversation.
    """
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    corrected_intent = body.get("corrected_intent")
    filled_slots = body.get("filled_slots")
    action = body.get("action", "none")
    notes = body.get("notes")
    filled_slots_json = json.dumps(filled_slots) if filled_slots is not None else None
    aid = append_human_action(
        conversation_id,
        trigger_reason=None,
        corrected_intent=corrected_intent,
        filled_slots_json=filled_slots_json,
        action=action,
        notes=notes,
    )
    if corrected_intent:
        update_nlp_results(conversation_id, primary_intent=corrected_intent)
    return {"conversation_id": conversation_id, "action_id": aid, "action": action}
