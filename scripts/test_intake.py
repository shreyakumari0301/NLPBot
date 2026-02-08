"""
Quick check that Phases 1–6 work: intake → process → state → completeness & lead → qualification.
Run with: from project root, server must be running (uvicorn src.main:app).
  python scripts/test_intake.py
"""
import os
import sys
from pathlib import Path

# allow importing src when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

# Use same env as server: from WSL use Windows host if server runs on Windows:
# export INTAKE_BASE_URL=http://$(grep nameserver /etc/resolv.conf | awk '{print $2}'):8000
BASE = os.environ.get("INTAKE_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 15


def main():
    # 1. Health
    r = requests.get(f"{BASE}/health", timeout=TIMEOUT)
    assert r.status_code == 200, f"Health failed: {r.status_code}"
    print("OK /health")

    # 2. Ingest chat
    payload = {
        "turns": [
            {"speaker_id": "agent", "text": "Hi, how can I help?"},
            {"speaker_id": "user", "text": "  I need a quote for a 2-minute animated ad.  "},
        ],
        "conversation_id": None,
    }
    r = requests.post(f"{BASE}/ingest/chat", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"Ingest failed: {r.status_code} {r.text}"
    data = r.json()
    cid = data["conversation_id"]
    print(f"OK POST /ingest/chat -> conversation_id = {cid}")

    # 3. Retrieve stored conversation (Phase 1 contract)
    r = requests.get(f"{BASE}/ingest/conversations/{cid}", timeout=TIMEOUT)
    assert r.status_code == 200, f"Get conversation failed: {r.status_code}"
    conv = r.json()
    assert conv["raw_transcript"], "raw_transcript should be set"
    assert conv.get("clean_text"), "clean_text should be set (normalization)"
    assert conv["conversation_metadata"]["channel_source"] == "chat"
    print("OK GET /ingest/conversations/{id}")
    print(f"  raw_transcript (first 80 chars): {conv['raw_transcript'][:80]}...")
    print(f"  clean_text (first 80 chars):    {conv['clean_text'][:80]}...")

    # 4. Phase 3 NLP process
    r = requests.post(f"{BASE}/ingest/conversations/{cid}/process", timeout=TIMEOUT)
    assert r.status_code == 200, f"Process failed: {r.status_code} {r.text}"
    proc = r.json()
    assert "final_intent" in proc and "extracted_entities" in proc
    print("OK POST /ingest/conversations/{id}/process")
    print(f"  final_intent: {proc['final_intent']['primary_intent']} (confidence: {proc['final_intent']['confidence']})")
    print(f"  extracted_entities: {proc['extracted_entities']}")

    # 5. GET again: persisted intent + entities
    r = requests.get(f"{BASE}/ingest/conversations/{cid}", timeout=TIMEOUT)
    assert r.status_code == 200
    conv = r.json()
    assert conv.get("primary_intent"), "primary_intent should be set after process"
    assert isinstance(conv.get("extracted_structured_fields"), dict), "extracted_structured_fields should be set"
    print("OK GET after process: primary_intent + extracted_structured_fields persisted")

    # 6. Phase 4: build state (slot map + follow-up)
    r = requests.post(f"{BASE}/ingest/conversations/{cid}/state", timeout=TIMEOUT)
    if r.status_code != 200:
        print(f"Build state failed: {r.status_code} {r.text}")
    assert r.status_code == 200, f"Build state failed: {r.status_code} {r.text}"
    state_resp = r.json()
    assert "state" in state_resp, "response should have state"
    state = state_resp["state"]
    assert state.get("intent"), "state should have intent"
    assert isinstance(state.get("slots"), dict), "state should have slots"
    # Phase 5 & 6: completeness and lead in POST /state response
    assert "completeness" in state_resp, "response should have completeness"
    assert "lead" in state_resp, "response should have lead"
    comp = state_resp["completeness"]
    lead = state_resp["lead"]
    assert "completeness_pct" in comp and "mandatory_fields_missing" in comp and "status" in comp
    assert "lead_score" in lead and "lead_band" in lead and "breakdown" in lead
    print("OK POST /ingest/conversations/{id}/state")
    print(f"  intent: {state['intent']}, stage: {state.get('stage')}")
    print(f"  completeness: {comp['completeness_pct']}% ({comp['status']}), missing: {comp['mandatory_fields_missing']}")
    print(f"  lead: {lead['lead_score']} ({lead['lead_band']})")
    print(f"  next_question: {(state_resp.get('next_question') or '')[:60]}...")
    print(f"  next_question_slot: {state_resp.get('next_question_slot')}")

    # 7. GET state
    r = requests.get(f"{BASE}/ingest/conversations/{cid}/state", timeout=TIMEOUT)
    assert r.status_code == 200
    get_state = r.json()
    assert get_state.get("state"), "GET state should return state"
    print("OK GET /ingest/conversations/{id}/state")

    # 8. GET qualification (Phase 5)
    r = requests.get(f"{BASE}/ingest/conversations/{cid}/qualification", timeout=TIMEOUT)
    assert r.status_code == 200, f"GET qualification failed: {r.status_code}"
    qual = r.json()
    assert qual.get("completeness") and qual.get("lead"), "qualification should have completeness and lead"
    print("OK GET /ingest/conversations/{id}/qualification")
    print(f"  completeness: {qual['completeness']['completeness_pct']}% ({qual['completeness']['status']})")
    print(f"  lead: {qual['lead']['lead_score']} ({qual['lead']['lead_band']})")
    print("Phases 1, 2, 3, 4, 5 & 6 are working.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.exceptions.ConnectionError:
        print("Error: Cannot reach server. Start with: uvicorn src.main:app --reload")
        print("  (Run server and script in the same environment: both WSL or both Windows.)")
        sys.exit(1)
    except requests.exceptions.ReadTimeout:
        print("Error: Request timed out. Is the server running in the same environment as this script?")
        print("  WSL script cannot reach 127.0.0.1 if the server is running in Windows (and vice versa).")
        sys.exit(1)
    except AssertionError as e:
        print(f"Fail: {e}")
        sys.exit(1)
