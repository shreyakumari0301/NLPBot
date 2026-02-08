# NLP Conversation Intelligence — AI Animation Production

**Phase 0:** Live processing (localhost). User and server both run locally.
**Intent catalog (MVP locked):** new_project_sales, price_estimation, general_services_query, complaint_issue, suggestion_feedback, career_hiring, unknown_chitchat. One primary intent at a time.
**Slot states (system-wide):** missing | filled | refused | unavailable.

**Phase 1:** One conversation → contract: `raw_transcript`, `primary_intent`, `secondary_tags`, `extracted_structured_fields`, `completeness_status`, `auto_generated_summary`, `lead_score`, `conversation_metadata` (+ `clean_text`, `speaker_turns`). See `src/schemas/contract.py`.

**Phase 2:** Intake flow:

```
Incoming Chat / Call → Channel Ingestion API → Conversation Registry
  → (Voice?) Transcription Worker → Text Normalization Worker
  → Raw + Clean Text Stored → Conversation Ready for NLP
```

## Run

```bash
cd c:\Users\shrey\NLPBot
pip install -r requirements.txt
uvicorn src.main:app --reload
```

**Voice bot (call with Mira):** Set `OPENAI_API_KEY` so the bot uses LangChain + OpenAI to understand and reply. For **local LLM** set `USE_OLLAMA=1` and run `ollama run mistral` (or `OLLAMA_MODEL=llama3`).

**Full-duplex voice agent (STT/TTS on server):** Install deps then use the "Use server STT+TTS" option on the call screen: records audio → `POST /live/audio` (faster-whisper + turn + optional TTS) → play reply. See `VOICE_AGENT.md` for VAD, interrupt, and Coqui XTTS.

- **POST /ingest/chat** — Send text chat (body: `{ "turns": [ { "speaker_id": "user", "text": "Hello" } ], "conversation_id": null }`).
- **POST /ingest/voice** — Send voice (body: `{ "transcript": "Pre-transcribed text" }` or `{ "audio_url": "https://..." }`).
- **GET /ingest/conversations/{conversation_id}** — Get stored conversation (raw + clean, metadata).
- **POST /ingest/conversations/{conversation_id}/process** — Run Phase 3 NLP (preprocess → intent → entity extraction); persists intent + entities.
- **GET /health** — Health check.

Data is stored in `data/conversations.db` (SQLite).

### Phase 3 NLP (re-runnable)

- **Preprocessing:** fillers removed, number words → digits, language detection (stub: en).
- **Intent:** tentative (first 3 turns) + final (full); one primary intent + confidence + secondary tags.
- **Entities:** content_type, style, duration_minutes, platform (stored even if incomplete).
- Intents: `sales_inquiry`, `estimation_request`, `order`, `complaint`, `suggestion`.

### Phase 4 — Conversation State & Slot Management

- **Intent Slot Registry** (`src/state/slot_registry.py`): per-intent required/optional slots; question templates and refusal phrases. Editable config, no ML.
- **Conversation state:** intent, slots (value + status: filled/missing/unavailable), confidence/source/timestamp per slot, last_question_asked, stage.
- **Step 4.1 — Slot map:** After each message, entity extraction → update slots (only if new value and higher confidence); refusal → slot unavailable. Recompute status vs required/optional.
- **Step 4.2 — Follow-up:** One question at a time by priority (name → country → content_type → …). Templates per slot; never repeat same phrasing; refusal moves on.
- **Stop:** All required filled, user says closure phrase, or stage = minimum_completeness_reached → actionable, stop asking.
- **Endpoints:** `GET /ingest/conversations/{id}/state`, `POST /ingest/conversations/{id}/state` (build from conversation), `POST /ingest/conversations/{id}/state/message` (append message, update state).

### Phase 5 — Completeness & Lead Qualification

- **Completeness status (separate from score):** `complete` | `actionable` (minor missing) | `incomplete` | `info_only`. Builds sales trust.
- **Completeness (5.1):** `completeness_pct` (0–100), `mandatory_fields_missing`, status as above.
- **Lead scoring (5.2):** Points (budget, timeline, clear animation type, contact); penalties (very short, vague, browsing). Score 0–100, bands: `cold` (0–30), `warm` (31–70), `hot` (71–100).
- **Endpoint:** `GET /ingest/conversations/{id}/qualification`. POST /state response includes `completeness` and `lead`.

### Phase 6 — Persistence & Traceability

- **Never overwrite, only append.** Raw transcript is set once; processed outputs and leads are versioned.
- **processing_runs:** Append-only table per run (state, completeness, lead score, breakdown).
- **leads:** Append-only table for final structured lead when status is actionable.
- **Endpoint:** POST /state appends to `processing_runs`; when actionable, appends to `leads`.

### Phase 7 — Company-Facing Dashboard

- **7.1 Home:** `GET /dashboard/home` — today's conversations, hot leads, estimation requests, complaints (business urgency first). `GET /dashboard/` — simple HTML dashboard UI.
- **7.2 Drill-down:** `GET /dashboard/conversations/{id}` — AI summary, intent & tags, extracted details, missing fields, full transcript; sales rarely need transcript (in details).

### Phase 8 — Human-in-the-Loop

- **Triggers:** intent confidence < 0.5, frustration detected (keywords), complaint intent → `needs_human` and `trigger_reasons` in drill-down.
- **Record takeover:** `POST /ingest/conversations/{id}/human-takeover` — body `{ "trigger_reason": "low_confidence"|"frustration_detected"|"complaint_intent" }`.
- **Human actions (gold data):** `POST /ingest/conversations/{id}/human-actions` — body `{ "corrected_intent", "filled_slots", "action": "close"|"convert"|"none", "notes" }`. Append-only `human_actions` table; optional update to conversation intent.

### Live conversation (call-centre style, localhost)

- **POST /live/start** — Start session; returns `session_id` and greeting: *"Hello sir, how may I help you?"*
- **POST /live/message** — Body: `{ "session_id", "user_message" }`. Bot replies live: captures slots, asks for missing required info, answers services/process/2D–3D queries from FAQ, notes complaints and asks name/reference. Interruption: *"Go ahead sir"* + answer, then continues. Sessions in-memory (localhost).
- **GET /live/session/{session_id}** — Debug: state and history.

**Call simulations (end-to-end):** Sim 1 Sales (Mira greeting → name → location → 2D/3D → budget). Sim 2 Interrupted query ("Sure, go ahead" → FAQ). Sim 3 Complaint ("I'm sorry to hear that. May I know your name so I can note this properly?" + log/escalate). Sim 4 Unknown ("Could you tell me what you're looking for today?").
