"""
Intent detection — MVP LOCKED. AI animation production company.
One primary intent active at any moment.
"""

import re
from dataclasses import dataclass

# MVP – Primary intents only
PRIMARY_INTENTS = [
    "new_project_sales",
    "price_estimation",
    "general_services_query",
    "complaint_issue",
    "suggestion_feedback",
    "career_hiring",
    "unknown_chitchat",
]

INTENT_SIGNALS = {
    "new_project_sales": [
        r"want\s+to\s+make\s+(an\s+)?animated",
        r"need\s+(a\s+)?promo\s+video",
        r"looking\s+for\s+animation",
        r"looking\s+for\s+animation\s+services",
        r"i\s+(am|m)\s+looking\s+for",
        r"animated\s+film", r"promo\s+video", r"animation\s+services",
        r"new\s+project", r"we\s+need\s+", r"make\s+(a\s+)?(short|film|video)",
        r"need\s+animation", r"want\s+animation",
    ],
    "price_estimation": [
        r"how\s+much\s+will\s+it\s+cost",
        r"budget\s+for", r"how\s+much", r"cost\s+", r"price\s+",
        r"quote", r"estimate", r"estimation", r"\d+d\s+short\s+film",
    ],
    "general_services_query": [
        r"what\s+services\s+(do\s+you\s+)?(offer|provide)",
        r"services\s+you\s+(offer|provide)",
        r"what\s+do\s+you\s+(offer|provide)",
        r"wh+t\s+do\s+you\s+offer",
        r"offer\s+(me|us)?\b",
        r"provide\b",
        r"company\s+about|about\s+(the\s+)?company",
        r"what\s+is\s+(this\s+)?company",
        r"tell\s+me\s+about\s+(you|your|company|services)",
        r"what\s+(do|does)\s+(this\s+)?(company|xyz)\b",
        r"do\s+you\s+do\s+2d\s+or\s+3d",
        r"what\s+is\s+your\s+process",
        r"services\s+you\s+offer",
        r"2d\s+or\s+3d",
        r"\b2d\b",
        r"\b3d\b",
        r"(2d|3d)\s+animation",
        r"animation\s+(2d|3d)",
        r"your\s+process",
    ],
    "complaint_issue": [
        r"not\s+happy\s+with\s+previous",
        r"delay\s+in\s+delivery", r"quality\s+issue",
        r"complaint", r"unhappy", r"disappointed", r"issue\s+with",
        r"refund", r"wrong\s+", r"not\s+what\s+i\s+expected",
    ],
    "suggestion_feedback": [
        r"i\s+have\s+an\s+idea", r"you\s+should\s+add",
        r"suggest", r"feedback", r"idea\s+", r"recommend",
    ],
    "career_hiring": [
        r"are\s+you\s+hiring", r"internship", r"job\s+opening",
        r"hiring", r"career", r"job\s+", r"intern",
    ],
    "unknown_chitchat": [
        r"hello", r"hi\b", r"hey\b", r"good\s+morning", r"thanks", r"bye",
    ],
}

TAG_PATTERNS = [
    ("short_film", re.compile(r"\b(short\s+film|short\s+video)\b", re.I)),
    ("series", re.compile(r"\b(series|episode)\b", re.I)),
    ("ad", re.compile(r"\b(ad|promo|commercial)\b", re.I)),
    ("explainer", re.compile(r"\bexplainer\b", re.I)),
    ("2d", re.compile(r"\b2d\b", re.I)),
    ("3d", re.compile(r"\b3d\b", re.I)),
    ("pixar_style", re.compile(r"\b(pixar|anime|realistic)\b", re.I)),
]


@dataclass
class IntentResult:
    primary_intent: str
    confidence: float
    secondary_tags: list[str]
    is_tentative: bool


def _normalize_for_intent(text: str) -> str:
    """Collapse repeated letters; fix 'i2d'/'i3d' so 2d/3d are detected."""
    t = text.lower().strip()
    if not t:
        return t
    t = re.sub(r"(.)\1+", r"\1", t)
    t = re.sub(r"\bi2d\b", "i 2d", t)
    t = re.sub(r"\bi3d\b", "i 3d", t)
    return t


def _score_intent(text: str) -> list[tuple[str, float]]:
    text_lower = text.lower()
    text_norm = _normalize_for_intent(text)
    scores: list[tuple[str, float]] = []
    for intent, patterns in INTENT_SIGNALS.items():
        count = sum(
            1 for p in patterns if re.search(p, text_lower) or re.search(p, text_norm)
        )
        conf = min(1.0, count / 3.0) if count else 0.0
        scores.append((intent, conf))
    return scores


def _pick_primary(scores: list[tuple[str, float]]) -> tuple[str, float]:
    best = max(scores, key=lambda x: x[1])
    if best[1] <= 0:
        return "unknown_chitchat", 0.2
    return best[0], round(best[1], 2)


def _extract_secondary_tags(text: str) -> list[str]:
    return [name for name, pat in TAG_PATTERNS if pat.search(text)]


def detect_intent(text: str, is_tentative: bool = False) -> IntentResult:
    if not text or not text.strip():
        return IntentResult(
            primary_intent="unknown_chitchat",
            confidence=0.0,
            secondary_tags=[],
            is_tentative=is_tentative,
        )
    scores = _score_intent(text)
    primary, confidence = _pick_primary(scores)
    tags = _extract_secondary_tags(text)
    return IntentResult(
        primary_intent=primary,
        confidence=confidence,
        secondary_tags=tags,
        is_tentative=is_tentative,
    )


def get_tentative_intent(text_first_n_turns: str, n_turns: int = 3) -> IntentResult:
    return detect_intent(text_first_n_turns, is_tentative=True)


def get_final_intent(full_conversation_text: str) -> IntentResult:
    return detect_intent(full_conversation_text, is_tentative=False)
