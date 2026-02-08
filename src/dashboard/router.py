"""
Phase 7: Company-facing dashboard API.
Home: today's conversations, hot leads, estimation requests, complaints.
Drill-down: summary, intent & tags, extracted details, missing fields, full transcript.
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from src.dashboard.page import DASHBOARD_HTML

from src.human import needs_human_takeover
from src.qualification import completeness_summary
from src.registry import (
    get_conversation,
    get_state_json,
    list_conversations_by_intent,
    list_conversations_today,
    list_hot_leads,
)
from src.state.models import ConversationState

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def dashboard_page():
    """Phase 7: Company-facing dashboard UI (home loads first: today, hot leads, estimates, complaints)."""
    return DASHBOARD_HTML


@router.get("/home")
def dashboard_home():
    """
    Phase 7.1: What loads first. Business urgency: today's conversations, hot leads,
    estimation requests, complaints.
    """
    today = list_conversations_today()
    hot = list_hot_leads()
    estimation_requests = list_conversations_by_intent("price_estimation")
    complaints = list_conversations_by_intent("complaint_issue")
    return {
        "todays_conversations": today,
        "hot_leads": hot,
        "estimation_requests": estimation_requests,
        "complaints": complaints,
    }


@router.get("/conversations/{conversation_id}")
def dashboard_drill_down(conversation_id: str):
    """
    Phase 7.2: Drill-down view. AI summary, intent & tags, extracted details,
    missing fields, full transcript. Sales rarely need full transcript.
    """
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    raw = get_state_json(conversation_id)
    missing: list[str] = []
    needs_human = False
    trigger_reasons: list[str] = []
    if raw:
        state = ConversationState.model_validate(json.loads(raw))
        comp = completeness_summary(state)
        missing = comp["mandatory_fields_missing"]
    confidence = conv.extracted_structured_fields.get("intent_confidence") if isinstance(conv.extracted_structured_fields.get("intent_confidence"), (int, float)) else None
    full_text = conv.clean_text or conv.raw_transcript or ""
    needs_human, trigger_reasons = needs_human_takeover(confidence, conv.primary_intent, full_text)
    return {
        "conversation_id": conversation_id,
        "summary": conv.auto_generated_summary,
        "intent": conv.primary_intent,
        "tags": conv.secondary_tags,
        "extracted_details": conv.extracted_structured_fields,
        "missing_fields": missing,
        "full_transcript": conv.raw_transcript,
        "needs_human": needs_human,
        "trigger_reasons": trigger_reasons,
    }
