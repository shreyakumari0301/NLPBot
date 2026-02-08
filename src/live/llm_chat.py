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
    use_ollama_env = os.environ.get("USE_OLLAMA", "").lower()
    ollama_disabled = use_ollama_env in ("0", "false", "no")

    # 1) Ollama: use if USE_OLLAMA=1 or if not disabled and no OpenAI key (default to local)
    if not ollama_disabled:
        try:
            from langchain_community.chat_models import ChatOllama

            _chat = ChatOllama(
                model=os.environ.get("OLLAMA_MODEL", "mistral"),
                temperature=0.8,
            )
            _llm_available = True
            return _chat
        except Exception:
            pass

    # 2) OpenAI (gpt-4o-mini) when OPENAI_API_KEY set or USE_OLLAMA=0
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


SYSTEM_PROMPT = """You are Mira, a friendly voice agent for XYZ Animations — we do 2D and 3D animation, short films, explainer videos, ads, and promos. You are speaking out loud on a call; sound natural and conversational, not like reading a script.

CRITICAL: Respond directly to what the user JUST said. Acknowledge briefly (e.g. "Sure —", "Got it —", "So you're looking for…") then answer or ask one short question. Never ignore what they said. Never repeat the same line.

- Keep replies SHORT: one or two short sentences. Natural spoken style, not formal or list-like.
- Move the conversation forward: "What would you like to go for?", "Need a quote?", "What kind of project?"
- Services / what we do: say we do that and ask what they want. Specific requests (e.g. "2D animation", "short film"): answer that, then one question.
- Stay in character as Mira. Do not say you're an AI or a language model."""


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
