"""
Phase 3 NLP pipeline: Preprocess (re-runnable) → Intent (tentative + final) → Entity extraction.
Updates conversation with primary intent, confidence, secondary tags, extracted fields.
"""

from src.nlp.entities import extract_entities, merge_entities
from src.nlp.intent import get_final_intent, get_tentative_intent
from src.nlp.preprocessing import preprocess

# Number of turns used for tentative intent
TENTATIVE_N_TURNS = 3


def run_nlp_pipeline(
    clean_text: str,
    speaker_turns_texts: list[str],
) -> dict:
    """
    Re-runnable pipeline. Returns dict with:
      preprocessed_text, language,
      tentative_intent, final_intent (each: primary_intent, confidence, secondary_tags),
      extracted_entities (structured fields).
    """
    # 3.1 Preprocessing (re-runnable)
    preprocessed = preprocess(clean_text)
    text_for_nlp = preprocessed.text or clean_text

    # 3.2 Intent: tentative from first N turns, then final from full
    first_n = "\n".join(speaker_turns_texts[:TENTATIVE_N_TURNS])
    tentative = get_tentative_intent(preprocess(first_n).text or first_n, n_turns=TENTATIVE_N_TURNS)
    final = get_final_intent(text_for_nlp)

    # 3.3 Entity extraction (store even incomplete)
    entities = extract_entities(text_for_nlp)

    return {
        "preprocessed_text": preprocessed.text,
        "language": preprocessed.language,
        "tentative_intent": {
            "primary_intent": tentative.primary_intent,
            "confidence": tentative.confidence,
            "secondary_tags": tentative.secondary_tags,
            "is_tentative": True,
        },
        "final_intent": {
            "primary_intent": final.primary_intent,
            "confidence": final.confidence,
            "secondary_tags": final.secondary_tags,
            "is_tentative": False,
        },
        "extracted_entities": entities,
    }


def run_and_persist(conversation_id: str, clean_text: str, speaker_turns_texts: list[str], update_registry) -> dict:
    """
    Run pipeline and persist final intent + entities to registry.
    Uses final intent as the single primary intent; secondary_tags merged.
    """
    result = run_nlp_pipeline(clean_text, speaker_turns_texts)
    final = result["final_intent"]
    entities = dict(result["extracted_entities"])
    entities["intent_confidence"] = final["confidence"]

    update_registry(
        conversation_id,
        primary_intent=final["primary_intent"],
        secondary_tags=final["secondary_tags"],
        extracted_fields=entities,
        language=result["language"],
    )
    return result
