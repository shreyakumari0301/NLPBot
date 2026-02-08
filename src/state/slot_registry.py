"""
Slot maps — FROZEN CONTRACT. Business truth, not NLP guesswork.
Slot state values: missing | filled | refused | unavailable (system-wide).
"""

from typing import TypedDict


class SlotConfig(TypedDict, total=False):
    question_templates: list[str]
    refusal_phrases: list[str]


# MVP – Frozen slot maps per intent
INTENT_SLOT_REGISTRY: dict[str, dict] = {
    "new_project_sales": {
        "required_slots": ["caller_name", "country_location", "project_type", "animation_type", "budget_or_range"],
        "optional_slots": ["duration", "deadline", "target_audience", "style_reference", "company_or_individual"],
        "slots_config": {
            "caller_name": {
                "question_templates": ["That's great! May I know your name?", "May I know your name, please?", "Can I get your name?"],
                "refusal_phrases": ["don't want to share", "prefer not", "skip", "rather not"],
            },
            "country_location": {
                "question_templates": ["Nice to meet you. Where are you calling from?", "From where are you calling?", "Which country or location are you based in?"],
                "refusal_phrases": ["don't want to share", "prefer not", "skip"],
            },
            "project_type": {
                "question_templates": ["What type of project is it—short film, series, ad, or explainer?", "Is it a short film, promo video, or something else?"],
                "refusal_phrases": ["not sure", "skip"],
            },
            "animation_type": {
                "question_templates": ["Thanks! Is this a 2D or 3D animation?", "Do you need 2D, 3D, or mixed animation?"],
                "refusal_phrases": ["no preference", "skip"],
            },
            "budget_or_range": {
                "question_templates": ["To guide you properly, do you have a budget in mind or would you like an estimate?", "Do you have a budget or budget range in mind?"],
                "refusal_phrases": ["confidential", "rather not", "skip"],
            },
            "duration": {"question_templates": ["What duration in seconds or minutes?"], "refusal_phrases": []},
            "deadline": {"question_templates": ["When do you need it by?"], "refusal_phrases": []},
            "target_audience": {"question_templates": ["Who is the target audience?"], "refusal_phrases": []},
            "style_reference": {"question_templates": ["Any style reference—Pixar, anime, realistic?"], "refusal_phrases": []},
            "company_or_individual": {"question_templates": ["Is this for a company or individual?"], "refusal_phrases": []},
        },
    },
    "price_estimation": {
        "required_slots": ["project_type", "animation_type", "approx_duration"],
        "optional_slots": ["budget_expectation", "deadline", "usage"],
        "slots_config": {
            "project_type": {"question_templates": ["What type of project—short film, ad, series?"], "refusal_phrases": []},
            "animation_type": {"question_templates": ["2D or 3D animation?"], "refusal_phrases": []},
            "approx_duration": {"question_templates": ["Approximate duration in minutes or seconds?"], "refusal_phrases": []},
            "budget_expectation": {"question_templates": ["Do you have a budget expectation?"], "refusal_phrases": []},
            "deadline": {"question_templates": ["Any deadline?"], "refusal_phrases": []},
            "usage": {"question_templates": ["Commercial or internal use?"], "refusal_phrases": []},
        },
    },
    "general_services_query": {
        "required_slots": [],
        "optional_slots": ["area_of_interest"],
        "slots_config": {"area_of_interest": {"question_templates": ["Which area—services, process, or timeline?"], "refusal_phrases": []}},
    },
    "complaint_issue": {
        "required_slots": ["name", "project_reference", "issue_category"],
        "optional_slots": ["desired_resolution"],
        "slots_config": {
            "name": {"question_templates": ["May I know your name?", "Who is calling?"], "refusal_phrases": []},
            "project_reference": {"question_templates": ["Do you have a project reference or order number?"], "refusal_phrases": []},
            "issue_category": {"question_templates": ["Is the issue regarding delay, quality, or communication?"], "refusal_phrases": []},
            "desired_resolution": {"question_templates": ["What resolution would you prefer?"], "refusal_phrases": []},
        },
    },
    "suggestion_feedback": {
        "required_slots": ["name", "suggestion_summary"],
        "optional_slots": [],
        "slots_config": {
            "name": {"question_templates": ["May I know your name?"], "refusal_phrases": []},
            "suggestion_summary": {"question_templates": ["Could you briefly describe your suggestion?"], "refusal_phrases": []},
        },
    },
    "career_hiring": {
        "required_slots": ["name", "role_interest"],
        "optional_slots": ["experience_level", "portfolio_mention"],
        "slots_config": {
            "name": {"question_templates": ["May I know your name?"], "refusal_phrases": []},
            "role_interest": {"question_templates": ["Which role are you interested in?"], "refusal_phrases": []},
            "experience_level": {"question_templates": ["What is your experience level?"], "refusal_phrases": []},
            "portfolio_mention": {"question_templates": ["Do you have a portfolio to share?"], "refusal_phrases": []},
        },
    },
    "unknown_chitchat": {
        "required_slots": [],
        "optional_slots": [],
        "slots_config": {},
    },
}

def _default_config() -> dict[str, SlotConfig]:
    return INTENT_SLOT_REGISTRY["new_project_sales"].get("slots_config", {})

DEFAULT_SLOTS_CONFIG: dict[str, SlotConfig] = _default_config()

# Priority order for asking (one at a time)
FOLLOW_UP_PRIORITY = [
    "caller_name", "name",
    "country_location",
    "project_type", "animation_type", "budget_or_range", "approx_duration",
    "duration", "deadline", "target_audience", "style_reference", "company_or_individual",
    "budget_expectation", "usage", "area_of_interest",
    "project_reference", "issue_category", "desired_resolution",
    "suggestion_summary", "role_interest", "experience_level", "portfolio_mention",
]


def get_required_slots(intent: str) -> list[str]:
    entry = INTENT_SLOT_REGISTRY.get(intent) or INTENT_SLOT_REGISTRY.get("unknown_chitchat", {})
    return list(entry.get("required_slots", []))


def get_optional_slots(intent: str) -> list[str]:
    entry = INTENT_SLOT_REGISTRY.get(intent) or INTENT_SLOT_REGISTRY.get("unknown_chitchat", {})
    return list(entry.get("optional_slots", []))


def get_slot_config(slot_name: str, intent: str | None = None) -> SlotConfig:
    if intent:
        entry = INTENT_SLOT_REGISTRY.get(intent, {})
        sc = entry.get("slots_config") or {}
        if slot_name in sc:
            return sc[slot_name]
    for _intent, data in INTENT_SLOT_REGISTRY.items():
        sc = data.get("slots_config") or {}
        if slot_name in sc:
            return sc[slot_name]
    return {}


def get_question_templates(slot_name: str, intent: str | None = None) -> list[str]:
    cfg = get_slot_config(slot_name, intent)
    return list(cfg.get("question_templates", ["Could you share that with me?"]))


def get_refusal_phrases(slot_name: str, intent: str | None = None) -> list[str]:
    cfg = get_slot_config(slot_name, intent)
    return list(cfg.get("refusal_phrases", []))
