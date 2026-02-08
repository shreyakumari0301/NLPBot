"""
LLM-backed reply for Mira using LangChain. Uses conversation history so the bot
understands and responds to what the user actually said instead of fixed templates.
"""

import os
from typing import Any

_llm_available: bool | None = None
_chat = None


def _get_chat():
    global _chat, _llm_available
    if _llm_available is False:
        return None
    if _chat is not None:
        return _chat
    # 1) Prefer local Ollama (Mistral / LLaMA-3 / Phi-3)
    if os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes"):
        try:
            from langchain_community.chat_models import ChatOllama

            _chat = ChatOllama(
                model=os.environ.get("OLLAMA_MODEL", "mistral"),
                temperature=0.7,
            )
            _llm_available = True
            return _chat
        except Exception:
            pass
    # 2) OpenAI (gpt-4o-mini)
    try:
        from langchain_openai import ChatOpenAI

        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            _llm_available = False
            return None
        _chat = ChatOpenAI(
            model=os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=key,
        )
        _llm_available = True
        return _chat
    except Exception:
        _llm_available = False
        return None


SYSTEM_PROMPT = """You are Mira, a friendly voice assistant for XYZ Animations — an animation and video production company.

Company: We do 2D and 3D animation, short films, explainer videos, ads, promos, and motion graphics. We handle the full pipeline from concept to delivery.

Your job:
- Answer naturally based on what the user said. Acknowledge their exact words and respond to their question or request.
- If they ask about services, pricing, quotes, or what you offer — explain clearly and offer to help with a quote or project details.
- If they ask "am I audible" or "can you hear me", say yes and ask them to go ahead.
- Keep replies concise and conversational (for voice: 1–3 sentences usually). Do not repeat the same generic line; vary your response to what they said.
- If you're not sure, ask a short follow-up or offer to connect them with the team.
- Never say you're an AI or that you have no preferences; stay in character as Mira from XYZ Animations."""


def get_llm_reply(history: list[dict[str, str]], user_message: str) -> str | None:
    """
    Get a reply from the LLM given conversation history and the latest user message.
    history: list of {"role": "user"|"bot", "text": "..."}
    Returns reply string or None if LLM not available or error.
    """
    chat = _get_chat()
    if not chat:
        return None
    if not (user_message or "").strip():
        return None
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for h in history:
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h.get("text") or ""))
            else:
                messages.append(AIMessage(content=h.get("text") or ""))
        messages.append(HumanMessage(content=user_message.strip()))
        response = chat.invoke(messages)
        content = getattr(response, "content", None) or str(response)
        return (content or "").strip() or None
    except Exception:
        return None
