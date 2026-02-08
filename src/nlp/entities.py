"""
Step 3.3 – Entity & Detail Extraction.
Map free text → structured fields. Store even if incomplete.
"""

import re
from typing import Any

# Content type signals
CONTENT_TYPE_PATTERNS = [
    ("short_film", re.compile(r"\b(short\s+film|short\s+video|short\s+clip|advertisement|\bad)\b", re.I)),
    ("feature", re.compile(r"\b(feature\s+film|feature\s+length|full\s+length)\b", re.I)),
    ("series", re.compile(r"\b(series|episode|web\s+series)\b", re.I)),
    ("commercial", re.compile(r"\b(commercial|promo|trailer)\b", re.I)),
]

# Style signals
STYLE_PATTERNS = [
    ("pixar_like", re.compile(r"\b(pixar|pixar-?like|pixar\s+style)\b", re.I)),
    ("2d", re.compile(r"\b(2d|2-d|traditional\s+animation)\b", re.I)),
    ("3d", re.compile(r"\b(3d|3-d|cgi)\b", re.I)),
    ("cartoon", re.compile(r"\b(cartoon|cartoon\s+style)\b", re.I)),
]

# Duration: "2 minutes", "2-minute", "five min", "30 sec"
DURATION_PATTERN = re.compile(
    r"(?:^|\s)(\d+(?:\.\d+)?)\s*[-]?\s*(min(?:ute)?s?|sec(?:ond)?s?|hr(?:s?)|hour(?:s?))\b",
    re.IGNORECASE,
)

# Platform
PLATFORM_PATTERNS = [
    ("youtube", re.compile(r"\byoutube\b", re.I)),
    ("instagram", re.compile(r"\binstagram\b", re.I)),
    ("tiktok", re.compile(r"\btiktok\b", re.I)),
    ("facebook", re.compile(r"\bfacebook\b", re.I)),
    ("tv", re.compile(r"\b(tv|television|broadcast)\b", re.I)),
    ("theatrical", re.compile(r"\b(theatrical|cinema|theater)\b", re.I)),
]


def _normalize_duration_to_minutes(match: re.Match) -> float:
    val = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("sec"):
        return round(val / 60, 2)
    if unit.startswith("hr") or unit.startswith("hour"):
        return val * 60
    return val


def extract_entities(text: str) -> dict[str, Any]:
    """
    Extract structured fields from conversation text.
    Returns dict with content_type, style, duration_minutes, platform, etc.
    Incomplete values are still stored (e.g. duration_minutes: null if not found).
    """
    result: dict[str, Any] = {
        "content_type": None,
        "style": None,
        "duration_minutes": None,
        "platform": None,
        "raw_duration_mentions": [],
    }
    if not text:
        return result

    # Content type (first match)
    for name, pat in CONTENT_TYPE_PATTERNS:
        if pat.search(text):
            result["content_type"] = name
            break

    # Style (first match)
    for name, pat in STYLE_PATTERNS:
        if pat.search(text):
            result["style"] = name
            break

    # Duration: collect all mentions, store primary as minutes
    for m in DURATION_PATTERN.finditer(text):
        mins = _normalize_duration_to_minutes(m)
        result["raw_duration_mentions"].append(f"{m.group(0).strip()} (~{mins} min)")
    if result["raw_duration_mentions"]:
        # Use first full-match duration in minutes
        first = re.search(DURATION_PATTERN, text)
        if first:
            result["duration_minutes"] = round(_normalize_duration_to_minutes(first), 2)

    # Platform (first match)
    for name, pat in PLATFORM_PATTERNS:
        if pat.search(text):
            result["platform"] = name
            break

    return result


def merge_entities(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge new extraction into existing; fill only missing keys. Store incomplete."""
    out = dict(existing)
    for k, v in new.items():
        if v is not None and (k not in out or out[k] is None):
            out[k] = v
        if k == "raw_duration_mentions" and new.get(k):
            out[k] = list(set((out.get(k) or []) + new[k]))
    return out
