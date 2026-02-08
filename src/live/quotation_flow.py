"""
Quotation flow helpers: detect user intent (quote request, reduce price, agree/reject, counter price).
"""

import re


def user_asks_for_quote(message: str) -> bool:
    """True if message clearly asks for a quote/price/quotation."""
    m = (message or "").strip().lower()
    if not m:
        return False
    patterns = [
        r"\b(quote|quotation|estimate|estimation|price|quoted)\b",
        r"how\s+much",
        r"what('s|s)\s+(the\s+)?(price|cost)",
        r"give\s+me\s+(a\s+)?(quote|quotation|estimate|price)",
        r"send\s+(me\s+)?(the\s+)?(quote|quotation|price)",
        r"(get|need|want)\s+(a\s+)?(quote|quotation|estimate|price)",
    ]
    return any(re.search(p, m) for p in patterns)


def user_asks_to_reduce_price(message: str) -> bool:
    """True if user is asking to reduce price / more discount."""
    m = (message or "").strip().lower()
    if not m:
        return False
    patterns = [
        r"\b(reduce|lower|discount|cheaper|less|bring\s+down)\b",
        r"can(\s+you)?\s+(reduce|lower|give\s+more\s+discount)",
        r"any\s+discount",
        r"reduce\s+(the\s+)?price",
    ]
    return any(re.search(p, m) for p in patterns)


def user_agrees(message: str) -> bool:
    """True if user is accepting (yes, ok, sure, agreed)."""
    m = (message or "").strip().lower()
    if not m:
        return False
    return m in ("yes", "ok", "sure", "agreed", "done", "fine", "sounds good", "go ahead") or m.startswith(("yes ", "ok ", "sure "))


def user_disagrees(message: str) -> bool:
    """True if user is declining (no, not really, can't)."""
    m = (message or "").strip().lower()
    if not m:
        return False
    return m in ("no", "nope", "not really", "can't", "cannot", "too high", "won't work") or m.startswith(("no ", "not "))


def extract_price_from_message(message: str) -> float | None:
    """Extract a numeric price from message (e.g. 50k, 50000, 40 thousand). Returns None if not found."""
    if not (message or "").strip():
        return None
    m = message.strip()
    # 50k, 50K, 1.5k -> 50000, 1500
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", m, re.I)
    if k_match:
        return float(k_match.group(1)) * 1000
    # 50 thousand, 40 lakh (optional)
    thou_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:thousand|thou)\b", m, re.I)
    if thou_match:
        return float(thou_match.group(1)) * 1000
    # Plain number (last number in message often is the price when they say "my budget is 50000")
    numbers = re.findall(r"\d{2,}(?:\.\d+)?", m)
    if numbers:
        return float(numbers[-1])
    single = re.findall(r"\b(\d+(?:\.\d+)?)\b", m)
    if single:
        return float(single[-1])
    return None
