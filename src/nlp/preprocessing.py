"""
Step 3.1 – Preprocessing Layer. Re-runnable on clean text.
Cleans fillers, normalizes number words, language detection (stub).
"""

import re
from dataclasses import dataclass

# Common fillers (English)
FILLER_PATTERN = re.compile(
    r"\b(uh+|um+|hmm+|hm+|ah+|er+|eh+|like\s+|you\s+know\s+|I\s+mean\s+)\b",
    re.IGNORECASE,
)

# Word → digit for duration/quantity (animated production context)
WORD_NUMS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "hundred": "100", "half": "0.5", "quarter": "0.25",
}
# "five minutes" → "5 minutes", "two minute" → "2 minute"
NUMBER_WORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in WORD_NUMS) + r")\s+(minute|minutes|min|sec|second|seconds|hr|hour|hours)\b",
    re.IGNORECASE,
)


@dataclass
class PreprocessResult:
    text: str
    language: str = "en"


def remove_fillers(text: str) -> str:
    """Remove filler words (uh, um, hmm, etc.). Re-runnable."""
    if not text:
        return ""
    return FILLER_PATTERN.sub(" ", text)


def normalize_number_words(text: str) -> str:
    """e.g. 'five minutes' → '5 minutes'. Re-runnable."""
    if not text:
        return ""

    def repl(m: re.Match) -> str:
        word, unit = m.group(1).lower(), m.group(2)
        num = WORD_NUMS.get(word, word)
        return f"{num} {unit}"

    return NUMBER_WORD_PATTERN.sub(repl, text)


def detect_language(text: str) -> str:
    """Language detection. English-only initially → always 'en'. Re-runnable."""
    # Stub: no external lib. Later plug in langdetect or similar.
    if not text or not text.strip():
        return "en"
    return "en"


def preprocess(text: str) -> PreprocessResult:
    """
    Full preprocessing: remove fillers → normalize number words → language.
    Idempotent / re-runnable.
    """
    if not text:
        return PreprocessResult("", "en")
    t = remove_fillers(text)
    t = normalize_number_words(t)
    t = re.sub(r"\s+", " ", t).strip()
    lang = detect_language(t)
    return PreprocessResult(t, lang)
