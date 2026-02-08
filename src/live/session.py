"""
Live conversation session — in-memory (localhost). Greet first, then capture slots, answer queries, remember context.
Quotation flow: create request on quote ask, 'few minutes'; admin sets quote → send amount + half discount;
bargain (half then full); ask user's price; admin exception → tell user, agree/reject.
"""

import uuid
from datetime import datetime
from typing import Any

from src.live.faq import get_faq_reply, LOOKING_FOR_ANIMATION_ANSWER, SERVICES_ANSWER
from src.live.llm_chat import get_llm_reply
from src.live.quotation_flow import (
    extract_price_from_message,
    user_agrees,
    user_asks_for_quote,
    user_asks_to_reduce_price,
    user_disagrees,
)
from src.nlp.intent import detect_intent
from src.registry import (
    create_quotation_request,
    get_quotation_by_id,
    get_quotation_by_session,
    update_quotation_discount_offered,
    update_quotation_status,
    update_quotation_user_price,
)
from src.state import get_next_question, update_state_from_message
from src.state.models import ConversationState, SlotStatus
from src.state.pipeline import initial_state
from src.state.slot_registry import get_question_templates, get_required_slots

# In-memory sessions (localhost only)
_sessions: dict[str, dict[str, Any]] = {}

# Sim 1 – Sales: Mira from XYZ Animations
GREETING = "Hello! This is Mira from XYZ Animations. How may I help you?"
# Sim 2 – Interrupted query
GO_AHEAD = "Sure, go ahead."
ALL_CAPTURED = "Thank you! We have all the details. To guide you properly, do you have a budget in mind or would you like an estimate? Is there anything else?"
# Sim 3 – Complaint
COMPLAINT_FIRST = "I'm sorry to hear that. May I know your name so I can note this properly?"
COMPLAINT_ACK = "We have noted your concern and will look into it. May I have your name and project reference so we can follow up?"
# Sim 4 – Unknown → intent clarification
UNKNOWN_CLARIFY = "Sure! Could you tell me what you're looking for today?"
# Quotation flow
QUOTE_FEW_MINUTES = "Please give me a few minutes to prepare your quotation. I'll get back to you shortly."
QUOTE_SENT = "Your quotation is Rs {amount:,.0f}. We can offer a discount of {discount_pct:.0f}%."
QUOTE_MORE_DISCOUNT = "We can extend the discount to {discount_pct:.0f}% — that would make it Rs {final:,.0f}."
QUOTE_GET_BACK = "I'll check and get back to you. What price would work for you?"
QUOTE_USER_PRICE_SAVED = "Noted. I'll get back to you with our best offer."
QUOTE_EXCEPTION_OFFER = "We can do it at Rs {amount:,.0f}. Would that work for you?"
QUOTE_AGREED = "Great, we'll process your order. You will receive confirmation shortly."
QUOTE_REJECTED = "Understood. If you change your mind or have another budget in mind, feel free to reach out."


def start_session() -> tuple[str, str]:
    """Returns (session_id, bot_reply). Bot says greeting first."""
    session_id = f"live_{uuid.uuid4().hex[:12]}"
    state = initial_state(None)
    _sessions[session_id] = {
        "state": state,
        "turn_index": 0,
        "history": [{"role": "bot", "text": GREETING}],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    return session_id, GREETING


def turn(session_id: str, user_message: str) -> tuple[str, ConversationState, str]:
    """
    Process one user message. Returns (bot_reply, updated_state, intent).
    - General query → FAQ answer; optionally "Go ahead sir" if mid-flow.
    - Else update slots; if missing required → ask next; if all filled → acknowledgment.
    - Complaint → note and ask name/reference if missing.
    """
    if session_id not in _sessions:
        return "Session not found. Please start a new conversation.", initial_state(None), "unknown_chitchat"
    data = _sessions[session_id]
    state: ConversationState = data["state"]
    turn_index = data["turn_index"]
    # "Am I audible?" / "Can you hear me?" — answer so user knows mic is working
    _msg = (user_message or "").strip().lower()
    if any(
        phrase in _msg
        for phrase in (
            "am i audible",
            "am i being heard",
            "can you hear me",
            "can u hear me",
            "do you hear me",
            "is my mic working",
            "mic check",
            "testing 1 2 3",
            "testing one two three",
            "hello can you hear",
            "are you there",
        )
    ):
        reply = "Yes, I can hear you. Go ahead."
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": reply})
        data["turn_index"] = turn_index + 1
        _sessions[session_id] = data
        return reply, state, "general_services_query"

    # LLM reply: capture what user said and respond naturally (LangChain)
    llm_reply = get_llm_reply(data["history"], user_message)
    if llm_reply:
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": llm_reply})
        data["turn_index"] = turn_index + 1
        _sessions[session_id] = data
        return llm_reply, state, "general_services_query"

    intent_result = detect_intent(user_message)
    intent = intent_result.primary_intent
    confidence = intent_result.confidence

    # Sim 4 – Unknown/chitchat → intent clarification
    if intent == "unknown_chitchat":
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": UNKNOWN_CLARIFY})
        data["turn_index"] = turn_index + 1
        return UNKNOWN_CLARIFY, state, intent

    # Sim 2 – General services query → "Sure, go ahead" if interrupted mid-flow, else FAQ
    if intent == "general_services_query":
        faq = get_faq_reply(user_message)
        reply = (GO_AHEAD + " " + faq) if state.last_question_asked else (faq or SERVICES_ANSWER)
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": reply})
        data["turn_index"] = turn_index + 1
        return reply, state, intent

    # Update intent if we had unknown/chitchat and now we have a clear intent
    if (state.intent is None or state.intent == "unknown_chitchat") and intent != "unknown_chitchat":
        state = state.model_copy(update={"intent": intent})
    elif state.intent is None:
        state = state.model_copy(update={"intent": intent})

    current_intent = state.intent or intent
    state = update_state_from_message(
        state,
        user_message,
        f"turn_{turn_index}",
        current_intent,
        is_user_turn=True,
    )

    # Sim 3 – Complaint: "I'm sorry to hear that. May I know your name..." (logs + escalates)
    if current_intent == "complaint_issue":
        required = get_required_slots(current_intent)
        missing = [r for r in required if (state.get_slot(r).status != SlotStatus.FILLED and state.get_slot(r).status != SlotStatus.REFUSED)]
        if missing:
            slot = missing[0]
            templates = get_question_templates(slot, current_intent)
            reply = COMPLAINT_FIRST if slot == "name" else (COMPLAINT_ACK + " " + (templates[0] if templates else "May I have your name and project reference?"))
        else:
            reply = "We have noted your complaint and will get back to you shortly. Is there anything else?"
        data["state"] = state
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": reply})
        data["turn_index"] = turn_index + 1
        _sessions[session_id] = data
        return reply, state, current_intent

    # ---------- Quotation flow ----------
    q = get_quotation_by_session(session_id)
    awaiting_qid = data.get("quotation_awaiting_acceptance")

    if awaiting_qid and q and q["id"] == awaiting_qid:
        # User is responding to exception offer
        if user_agrees(user_message):
            update_quotation_status(q["id"], "agreed")
            data["quotation_awaiting_acceptance"] = None
            reply = QUOTE_AGREED
        elif user_disagrees(user_message):
            reason = f"User declined exception price of Rs {q.get('admin_exception_amount') or 0:,.0f}"
            update_quotation_status(q["id"], "rejected", rejection_reason=reason)
            data["quotation_awaiting_acceptance"] = None
            reply = QUOTE_REJECTED
        else:
            reply = "Would that price work for you? Please say yes or no."
        data["state"] = state
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": reply})
        data["turn_index"] = turn_index + 1
        _sessions[session_id] = data
        return reply, state, current_intent

    if q and q["status"] == "quote_ready":
        amount = q.get("admin_quoted_amount") or 0
        max_disc = q.get("admin_max_discount_pct") or 0
        half_disc = max(0, min(max_disc, round(max_disc / 2, 1)))
        update_quotation_discount_offered(q["id"], half_disc)
        update_quotation_status(q["id"], "sent_to_user")
        reply = QUOTE_SENT.format(amount=amount, discount_pct=half_disc)
        data["state"] = state
        data["history"].append({"role": "user", "text": user_message})
        data["history"].append({"role": "bot", "text": reply})
        data["turn_index"] = turn_index + 1
        _sessions[session_id] = data
        return reply, state, current_intent

    if q and q["status"] in ("sent_to_user", "negotiating"):
        quoted = q.get("admin_quoted_amount") or 0
        max_disc = q.get("admin_max_discount_pct") or 0
        offered = q.get("discount_offered_to_user_pct") or 0
        exception_amount = q.get("admin_exception_amount")

        # Admin set exception: offer it to user (once)
        if exception_amount is not None and not data.get("quotation_awaiting_acceptance"):
            data["quotation_awaiting_acceptance"] = q["id"]
            reply = QUOTE_EXCEPTION_OFFER.format(amount=exception_amount)
            data["state"] = state
            data["history"].append({"role": "user", "text": user_message})
            data["history"].append({"role": "bot", "text": reply})
            data["turn_index"] = turn_index + 1
            _sessions[session_id] = data
            return reply, state, current_intent

        if user_asks_to_reduce_price(user_message):
            if offered < max_disc:
                # Offer more: half of remaining, then full (human-like)
                remaining = max_disc - offered
                add = min(remaining, max(remaining / 2, 1))
                new_offered = min(max_disc, offered + add)
                update_quotation_discount_offered(q["id"], new_offered)
                final_price = quoted * (1 - new_offered / 100)
                reply = QUOTE_MORE_DISCOUNT.format(discount_pct=new_offered, final=final_price)
            else:
                reply = QUOTE_GET_BACK
                price = extract_price_from_message(user_message)
                if price is not None:
                    update_quotation_user_price(q["id"], price)
                    reply = QUOTE_GET_BACK + " " + QUOTE_USER_PRICE_SAVED
            data["state"] = state
            data["history"].append({"role": "user", "text": user_message})
            data["history"].append({"role": "bot", "text": reply})
            data["turn_index"] = turn_index + 1
            _sessions[session_id] = data
            return reply, state, current_intent

        price = extract_price_from_message(user_message)
        if price is not None and q.get("user_counter_price") is None:
            update_quotation_user_price(q["id"], price)
            reply = QUOTE_USER_PRICE_SAVED
            data["state"] = state
            data["history"].append({"role": "user", "text": user_message})
            data["history"].append({"role": "bot", "text": reply})
            data["turn_index"] = turn_index + 1
            _sessions[session_id] = data
            return reply, state, current_intent

    # Create new quotation request when user asks for quote (price_estimation)
    if current_intent == "price_estimation" and user_asks_for_quote(user_message):
        if not q or q["status"] in ("agreed", "rejected"):
            req_id = create_quotation_request(session_id)
            data["quotation_request_id"] = req_id
            reply = QUOTE_FEW_MINUTES
            data["state"] = state
            data["history"].append({"role": "user", "text": user_message})
            data["history"].append({"role": "bot", "text": reply})
            data["turn_index"] = turn_index + 1
            _sessions[session_id] = data
            return reply, state, current_intent

    # Other intents: check required slots
    required = get_required_slots(current_intent)
    if not required:
        reply = ALL_CAPTURED
    else:
        question, slot = get_next_question(state, turn_index=turn_index, last_user_message=user_message)
        if question:
            reply = question
            # First reply for "looking for animation" — acknowledge then ask (agentic)
            if (
                current_intent == "new_project_sales"
                and slot
                and not state.get_slot(slot).value
                and ("looking for" in user_message.lower() or "animation" in user_message.lower())
            ):
                reply = LOOKING_FOR_ANIMATION_ANSWER + " " + question
        else:
            reply = ALL_CAPTURED

    data["state"] = state
    data["history"].append({"role": "user", "text": user_message})
    data["history"].append({"role": "bot", "text": reply})
    data["turn_index"] = turn_index + 1
    _sessions[session_id] = data
    return reply, state, current_intent


def get_session(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)
