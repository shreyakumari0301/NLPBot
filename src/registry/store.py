"""Conversation Registry: persist conversation ID, speaker turns, timestamps, channel."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.schemas import ChannelSource, ConversationOutput, SpeakerTurn
from src.schemas.contract import CompletenessStatus, ConversationMetadata

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "conversations.db"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                channel_source TEXT NOT NULL,
                raw_transcript TEXT NOT NULL,
                clean_text TEXT,
                speaker_turns_json TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                language TEXT DEFAULT 'en',
                primary_intent TEXT,
                secondary_tags_json TEXT,
                extracted_fields_json TEXT,
                completeness_status TEXT DEFAULT 'unknown',
                auto_summary TEXT,
                lead_score REAL,
                geo_metadata_json TEXT,
                state_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Add state_json if missing (e.g. table created by older code)
        try:
            info = c.execute("PRAGMA table_info(conversations)").fetchall()
            cols = [row[1] for row in info]
            if "state_json" not in cols:
                c.execute("ALTER TABLE conversations ADD COLUMN state_json TEXT")
        except sqlite3.OperationalError:
            pass
        # Phase 6: append-only tables (never overwrite)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                nlp_output_json TEXT,
                state_json TEXT,
                completeness_pct INTEGER,
                mandatory_missing_json TEXT,
                completeness_label TEXT,
                lead_score REAL,
                lead_band TEXT,
                lead_breakdown_json TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                intent TEXT,
                slots_json TEXT,
                completeness_pct INTEGER,
                completeness_label TEXT,
                lead_score REAL,
                lead_band TEXT,
                lead_breakdown_json TEXT
            )
            """
        )
        # Phase 8: human corrections (gold data), append-only
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS human_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                trigger_reason TEXT,
                corrected_intent TEXT,
                filled_slots_json TEXT,
                action TEXT,
                notes TEXT
            )
            """
        )
        # Phase 7: lead_band on conversations for dashboard filter
        try:
            info = c.execute("PRAGMA table_info(conversations)").fetchall()
            cols = [row[1] for row in info]
            if "lead_band" not in cols:
                c.execute("ALTER TABLE conversations ADD COLUMN lead_band TEXT")
        except sqlite3.OperationalError:
            pass
        # Quotation/order flow (live sessions)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS quotation_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_quote',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                admin_quoted_amount REAL,
                admin_max_discount_pct REAL,
                discount_offered_to_user_pct REAL DEFAULT 0,
                user_counter_price REAL,
                admin_exception_amount REAL,
                rejection_reason TEXT,
                is_urgent INTEGER DEFAULT 0,
                request_summary TEXT
            )
            """
        )


def _turns_from_row(row: sqlite3.Row) -> list[SpeakerTurn]:
    raw = row["speaker_turns_json"]
    if not raw:
        return []
    data = json.loads(raw)
    return [SpeakerTurn(**t) for t in data]


def register_conversation(
    conversation_id: str,
    channel_source: ChannelSource,
    speaker_turns: list[SpeakerTurn],
    raw_transcript: str,
    clean_text: str | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> None:
    turns_json = json.dumps(
        [t.model_dump(mode="json") for t in speaker_turns],
        default=str,
    )
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO conversations (
                conversation_id, channel_source, raw_transcript, clean_text,
                speaker_turns_json, started_at, ended_at, language,
                primary_intent, secondary_tags_json, extracted_fields_json,
                completeness_status, auto_summary, lead_score, geo_metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'en', NULL, '[]', '{}', ?, NULL, NULL, '{}', ?, ?)
            """,
            (
                conversation_id,
                channel_source.value,
                raw_transcript,
                clean_text,
                turns_json,
                started_at,
                ended_at,
                CompletenessStatus.UNKNOWN.value,
                now,
                now,
            ),
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def get_conversation(conversation_id: str) -> ConversationOutput | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    if not row:
        return None
    turns = _turns_from_row(row)
    meta = ConversationMetadata(
        conversation_id=row["conversation_id"],
        channel_source=ChannelSource(row["channel_source"]),
        started_at=_parse_iso(row["started_at"]),
        ended_at=_parse_iso(row["ended_at"]),
        language=row["language"] or "en",
        geo_metadata=json.loads(row["geo_metadata_json"] or "{}"),
    )
    return ConversationOutput(
        conversation_id=row["conversation_id"],
        raw_transcript=row["raw_transcript"],
        primary_intent=row["primary_intent"],
        secondary_tags=json.loads(row["secondary_tags_json"] or "[]"),
        extracted_structured_fields=json.loads(row["extracted_fields_json"] or "{}"),
        completeness_status=CompletenessStatus(row["completeness_status"] or "unknown"),
        auto_generated_summary=row["auto_summary"],
        lead_score=row["lead_score"],
        conversation_metadata=meta,
        clean_text=row["clean_text"],
        speaker_turns=turns,
    )


def update_nlp_results(
    conversation_id: str,
    *,
    primary_intent: str | None = None,
    secondary_tags: list[str] | None = None,
    extracted_fields: dict | None = None,
    language: str | None = None,
) -> bool:
    """Update NLP fields for a conversation. Returns True if row existed."""
    with _conn() as c:
        row = c.execute(
            "SELECT primary_intent, secondary_tags_json, extracted_fields_json, language FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if not row:
            return False
        now = datetime.utcnow().isoformat() + "Z"
        intent = primary_intent if primary_intent is not None else row["primary_intent"]
        tags = json.dumps(secondary_tags) if secondary_tags is not None else row["secondary_tags_json"]
        fields = json.dumps(extracted_fields) if extracted_fields is not None else row["extracted_fields_json"]
        lang = language if language is not None else row["language"]
        c.execute(
            """
            UPDATE conversations
            SET primary_intent = ?, secondary_tags_json = ?, extracted_fields_json = ?, language = ?, updated_at = ?
            WHERE conversation_id = ?
            """,
            (intent, tags, fields, lang, now, conversation_id),
        )
    return True


def get_state_json(conversation_id: str) -> str | None:
    """Raw state JSON for conversation. None if not set."""
    with _conn() as c:
        row = c.execute(
            "SELECT state_json FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    return row["state_json"] if row and row["state_json"] else None


def save_state_json(conversation_id: str, state_json: str) -> bool:
    with _conn() as c:
        now = datetime.utcnow().isoformat() + "Z"
        cur = c.execute(
            "UPDATE conversations SET state_json = ?, updated_at = ? WHERE conversation_id = ?",
            (state_json, now, conversation_id),
        )
        return cur.rowcount > 0


def update_completeness_status(conversation_id: str, status: str) -> bool:
    with _conn() as c:
        now = datetime.utcnow().isoformat() + "Z"
        cur = c.execute(
            "UPDATE conversations SET completeness_status = ?, updated_at = ? WHERE conversation_id = ?",
            (status, now, conversation_id),
        )
        return cur.rowcount > 0


def update_lead_score(conversation_id: str, lead_score: float, lead_band: str | None = None) -> bool:
    with _conn() as c:
        now = datetime.utcnow().isoformat() + "Z"
        if lead_band is not None:
            cur = c.execute(
                "UPDATE conversations SET lead_score = ?, lead_band = ?, updated_at = ? WHERE conversation_id = ?",
                (lead_score, lead_band, now, conversation_id),
            )
        else:
            cur = c.execute(
                "UPDATE conversations SET lead_score = ?, updated_at = ? WHERE conversation_id = ?",
                (lead_score, now, conversation_id),
            )
        return cur.rowcount > 0


def append_processing_run(
    conversation_id: str,
    *,
    nlp_output_json: str | None = None,
    state_json: str | None = None,
    completeness_pct: int | None = None,
    mandatory_missing_json: str | None = None,
    completeness_label: str | None = None,
    lead_score: float | None = None,
    lead_band: str | None = None,
    lead_breakdown_json: str | None = None,
) -> int:
    """Phase 6: Append one processing run (versioned). Never overwrite. Returns run_id."""
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO processing_runs (
                conversation_id, created_at, nlp_output_json, state_json,
                completeness_pct, mandatory_missing_json, completeness_label,
                lead_score, lead_band, lead_breakdown_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                now,
                nlp_output_json,
                state_json,
                completeness_pct,
                mandatory_missing_json,
                completeness_label,
                lead_score,
                lead_band,
                lead_breakdown_json,
            ),
        )
        return cur.lastrowid or 0


def append_lead(
    conversation_id: str,
    *,
    intent: str | None = None,
    slots_json: str | None = None,
    completeness_pct: int | None = None,
    completeness_label: str | None = None,
    lead_score: float | None = None,
    lead_band: str | None = None,
    lead_breakdown_json: str | None = None,
) -> int:
    """Phase 6: Append one final structured lead. Never overwrite. Returns lead_id."""
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO leads (
                conversation_id, created_at, intent, slots_json,
                completeness_pct, completeness_label, lead_score, lead_band, lead_breakdown_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                now,
                intent,
                slots_json,
                completeness_pct,
                completeness_label,
                lead_score,
                lead_band,
                lead_breakdown_json,
            ),
        )
        return cur.lastrowid or 0


def list_conversations_today() -> list[dict]:
    """Phase 7: Conversations created today (UTC date)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _conn() as c:
        try:
            cur = c.execute(
                """
                SELECT conversation_id, created_at, primary_intent, lead_score, lead_band, completeness_status
                FROM conversations WHERE date(created_at) = ?
                ORDER BY created_at DESC
                """,
                (today,),
            )
        except sqlite3.OperationalError:
            cur = c.execute(
                """
                SELECT conversation_id, created_at, primary_intent, lead_score, completeness_status
                FROM conversations WHERE date(created_at) = ?
                ORDER BY created_at DESC
                """,
                (today,),
            )
        rows = cur.fetchall()
    return [_row_to_dashboard_row(r) for r in rows]


def list_hot_leads() -> list[dict]:
    """Phase 7: Hot leads (lead_band = 'hot' or lead_score >= 71)."""
    with _conn() as c:
        try:
            cur = c.execute(
                """
                SELECT conversation_id, created_at, primary_intent, lead_score, lead_band, completeness_status
                FROM conversations WHERE lead_band = 'hot' OR lead_score >= 71
                ORDER BY created_at DESC
                """
            )
        except sqlite3.OperationalError:
            cur = c.execute(
                """
                SELECT conversation_id, created_at, primary_intent, lead_score, completeness_status
                FROM conversations WHERE lead_score >= 71
                ORDER BY created_at DESC
                """
            )
        rows = cur.fetchall()
    return [_row_to_dashboard_row(r) for r in rows]


def list_conversations_by_intent(intent: str) -> list[dict]:
    """Phase 7: Filter by primary_intent (e.g. estimation_request, complaint)."""
    with _conn() as c:
        cur = c.execute(
            """
            SELECT conversation_id, created_at, primary_intent, lead_score, lead_band, completeness_status
            FROM conversations WHERE primary_intent = ?
            ORDER BY created_at DESC
            """,
            (intent,),
        )
        rows = cur.fetchall()
    return [_row_to_dashboard_row(r) for r in rows]


def _row_to_dashboard_row(r: sqlite3.Row) -> dict:
    return {k: r[k] for k in r.keys()}


def append_human_action(
    conversation_id: str,
    *,
    trigger_reason: str | None = None,
    corrected_intent: str | None = None,
    filled_slots_json: str | None = None,
    action: str | None = None,
    notes: str | None = None,
) -> int:
    """Phase 8: Append human correction (gold data). Returns action_id."""
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO human_actions (
                conversation_id, created_at, trigger_reason, corrected_intent,
                filled_slots_json, action, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, now, trigger_reason, corrected_intent, filled_slots_json, action, notes),
        )
        return cur.lastrowid or 0


def generate_conversation_id() -> str:
    return f"conv_{uuid.uuid4().hex[:16]}"


# ---------- Quotation / order flow (live sessions) ----------

def create_quotation_request(session_id: str, request_summary: str | None = None) -> int:
    """Create a pending quotation request. Returns id."""
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO quotation_requests (
                session_id, status, created_at, updated_at, request_summary
            ) VALUES (?, 'pending_quote', ?, ?, ?)
            """,
            (session_id, now, now, request_summary or ""),
        )
        return cur.lastrowid or 0


def get_quotation_by_session(session_id: str) -> dict | None:
    """Latest quotation request for this session (for live flow)."""
    with _conn() as c:
        row = c.execute(
            """
            SELECT * FROM quotation_requests WHERE session_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    return _quotation_row_to_dict(row) if row else None


def get_quotation_by_id(qid: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM quotation_requests WHERE id = ?", (qid,)).fetchone()
    return _quotation_row_to_dict(row) if row else None


def _quotation_row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "admin_quoted_amount": row["admin_quoted_amount"],
        "admin_max_discount_pct": row["admin_max_discount_pct"],
        "discount_offered_to_user_pct": row["discount_offered_to_user_pct"] or 0,
        "user_counter_price": row["user_counter_price"],
        "admin_exception_amount": row["admin_exception_amount"],
        "rejection_reason": row["rejection_reason"],
        "is_urgent": bool(row["is_urgent"]),
        "request_summary": row["request_summary"],
    }


def list_quotation_requests(urgent_only: bool = False) -> list[dict]:
    with _conn() as c:
        if urgent_only:
            cur = c.execute(
                """
                SELECT * FROM quotation_requests WHERE is_urgent = 1
                ORDER BY created_at DESC
                """
            )
        else:
            cur = c.execute(
                "SELECT * FROM quotation_requests ORDER BY created_at DESC"
            )
        rows = cur.fetchall()
    return [_quotation_row_to_dict(r) for r in rows if r]


def update_quotation_quote(qid: int, amount: float, max_discount_pct: float) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE quotation_requests
            SET admin_quoted_amount = ?, admin_max_discount_pct = ?, status = 'quote_ready', updated_at = ?
            WHERE id = ?
            """,
            (amount, max_discount_pct, now, qid),
        )
        return cur.rowcount > 0


def set_quotation_urgent(qid: int, is_urgent: bool = True) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            "UPDATE quotation_requests SET is_urgent = ?, updated_at = ? WHERE id = ?",
            (1 if is_urgent else 0, now, qid),
        )
        return cur.rowcount > 0


def update_quotation_user_price(qid: int, user_price: float) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE quotation_requests
            SET user_counter_price = ?, status = 'negotiating', updated_at = ?
            WHERE id = ?
            """,
            (user_price, now, qid),
        )
        return cur.rowcount > 0


def update_quotation_exception(qid: int, exception_amount: float) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE quotation_requests
            SET admin_exception_amount = ?, updated_at = ?
            WHERE id = ?
            """,
            (exception_amount, now, qid),
        )
        return cur.rowcount > 0


def update_quotation_status(
    qid: int, status: str, rejection_reason: str | None = None
) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        if rejection_reason is not None:
            cur = c.execute(
                """
                UPDATE quotation_requests SET status = ?, rejection_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, rejection_reason, now, qid),
            )
        else:
            cur = c.execute(
                "UPDATE quotation_requests SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, qid),
            )
        return cur.rowcount > 0


def update_quotation_discount_offered(qid: int, discount_pct: float) -> bool:
    now = datetime.utcnow().isoformat() + "Z"
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE quotation_requests SET discount_offered_to_user_pct = ?, updated_at = ?
            WHERE id = ?
            """,
            (discount_pct, now, qid),
        )
        return cur.rowcount > 0
