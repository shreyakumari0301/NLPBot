"""FAQ for General Services Query — conversational answers about company, services, process."""

SERVICES_ANSWER = (
    "We provide 2D, 3D, explainer videos, ads, and full animated films. "
    "Would you like details on any specific service?"
)
COMPANY_ANSWER = (
    "XYZ Animations is an animation and video production studio. "
    "We do 2D and 3D animation, short films, promos, ads, and motion graphics — "
    "from concept to delivery. What would you like to know more about?"
)
PROCESS_ANSWER = (
    "Our process: brief and concept, script and storyboard, style and asset design, "
    "animation, review and revision, then final delivery. Timelines depend on scope. "
    "Anything specific you'd like to know?"
)
TWO_D_OR_3D_ANSWER = (
    "We do both 2D and 3D animation, and mixed projects. "
    "Do you have a style in mind for your project?"
)
LOOKING_FOR_ANIMATION_ANSWER = (
    "Great — we do 2D and 3D animation, short films, ads, and explainers. "
    "Do you have a project in mind? I can help with a quote or walk you through our process."
)

SERVICES_KEYWORDS = ["services", "offer", "what do you", "provide", "do you do"]
COMPANY_KEYWORDS = ["company", "about", "this company", "xyz"]
PROCESS_KEYWORDS = ["process", "how do you", "how does it work", "timeline", "steps"]
TWO_D_3D_KEYWORDS = ["2d", "3d", "two d", "three d", "animation style"]
LOOKING_KEYWORDS = ["looking for", "need animation", "want animation", "animations"]


def get_faq_reply(user_message: str) -> str | None:
    msg = (user_message or "").strip().lower()
    if not msg:
        return None
    if any(k in msg for k in TWO_D_3D_KEYWORDS):
        return TWO_D_OR_3D_ANSWER
    if any(k in msg for k in PROCESS_KEYWORDS):
        return PROCESS_ANSWER
    if any(k in msg for k in COMPANY_KEYWORDS):
        return COMPANY_ANSWER
    if any(k in msg for k in LOOKING_KEYWORDS):
        return LOOKING_FOR_ANIMATION_ANSWER
    if any(k in msg for k in SERVICES_KEYWORDS):
        return SERVICES_ANSWER
    return SERVICES_ANSWER
