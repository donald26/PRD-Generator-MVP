"""
SQLite Persistence Layer for Phased PRD Generation.

Provides durable persistence for the entire phased flow:
sessions, questionnaires, documents, phase gates, generation progress,
artifacts, HITL edits, and an immutable audit log.
"""
import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

LOG = logging.getLogger("backend.store.phase_store")


class PhaseStore:
    """SQLite-backed persistence for phased PRD generation sessions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a connection with row_factory set."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Create all tables if they don't exist. Enable WAL mode."""
        conn = self._get_conn()
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            LOG.info(f"PhaseStore initialized: {self.db_path}")
        finally:
            conn.close()

    # --- Session lifecycle ---
    def create_session(self, session_id: str, flow_type: str) -> dict:
        now = _now()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO sessions (id, flow_type, status, created_at, updated_at)
                   VALUES (?, ?, 'intake', ?, ?)""",
                (session_id, flow_type, now, now),
            )
            conn.commit()
            return self.get_session(session_id)
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_session(self, session_id: str, **kwargs):
        if not kwargs:
            return
        kwargs["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id]
        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE sessions SET {set_clause} WHERE id = ?", values
            )
            conn.commit()
        finally:
            conn.close()

    def list_sessions(self, status: str = None, limit: int = 50) -> list:
        conn = self._get_conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Questionnaire ---
    def save_questionnaire(self, session_id: str, questions: list, answers: dict):
        """Store question_text + mapping alongside answer for audit."""
        now = _now()
        conn = self._get_conn()
        try:
            for q in questions:
                qid = q["id"]
                answer = answers.get(qid, "")
                mapping_json = json.dumps(q.get("mapping", []))
                conn.execute(
                    """INSERT OR REPLACE INTO questionnaire_responses
                       (session_id, question_id, question_text, answer, mapping, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (session_id, qid, q["question_text"], answer, mapping_json, now),
                )
            conn.commit()
        finally:
            conn.close()

    def get_questionnaire(self, session_id: str) -> dict:
        """Return answers as {question_id: answer} plus metadata."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM questionnaire_responses WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            answers = {}
            questions = []
            for r in rows:
                r_dict = dict(r)
                answers[r_dict["question_id"]] = r_dict["answer"]
                questions.append(r_dict)
            return {"answers": answers, "responses": questions}
        finally:
            conn.close()

    # --- Documents ---
    def save_document(self, session_id: str, filename: str, file_path: str,
                      file_size: int, file_type: str, content_hash: str):
        now = _now()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO session_documents
                   (session_id, filename, file_path, file_size, file_type, content_hash, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, filename, file_path, file_size, file_type, content_hash, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_documents(self, session_id: str) -> list:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM session_documents WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Phase gates ---
    def create_phase_gate(self, session_id: str, phase_number: int,
                          phase_name: str) -> dict:
        now = _now()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO phase_gates
                   (session_id, phase_number, phase_name, status, started_at)
                   VALUES (?, ?, ?, 'generating', ?)""",
                (session_id, phase_number, phase_name, now),
            )
            conn.commit()
            return self.get_phase_gate(session_id, phase_number)
        finally:
            conn.close()

    def update_phase_gate(self, session_id: str, phase_number: int, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id, phase_number]
        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE phase_gates SET {set_clause} WHERE session_id = ? AND phase_number = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    def get_phase_gate(self, session_id: str, phase_number: int) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM phase_gates WHERE session_id = ? AND phase_number = ?",
                (session_id, phase_number),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_phase_gates(self, session_id: str) -> list:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM phase_gates WHERE session_id = ? ORDER BY phase_number",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Generation progress ---
    def init_generation_progress(self, phase_gate_id: int, artifact_types: list):
        conn = self._get_conn()
        try:
            for at in artifact_types:
                conn.execute(
                    """INSERT OR IGNORE INTO generation_progress
                       (phase_gate_id, artifact_type, status)
                       VALUES (?, ?, 'pending')""",
                    (phase_gate_id, at),
                )
            conn.commit()
        finally:
            conn.close()

    def update_artifact_progress(self, phase_gate_id: int,
                                 artifact_type: str, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [phase_gate_id, artifact_type]
        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE generation_progress SET {set_clause} WHERE phase_gate_id = ? AND artifact_type = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    def get_generation_progress(self, phase_gate_id: int) -> list:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM generation_progress WHERE phase_gate_id = ? ORDER BY id",
                (phase_gate_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_incomplete_artifacts(self, phase_gate_id: int) -> list:
        """For resume: returns artifacts not yet 'completed' or 'cached'."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM generation_progress
                   WHERE phase_gate_id = ? AND status NOT IN ('completed', 'cached')
                   ORDER BY id""",
                (phase_gate_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Phase artifacts ---
    def save_phase_artifact(self, phase_gate_id: int, artifact_type: str,
                            content_hash: str, file_path: str,
                            char_count: int, was_edited: bool = False):
        now = _now()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO phase_artifacts
                   (phase_gate_id, artifact_type, content_hash, file_path, char_count, was_edited, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (phase_gate_id, artifact_type, content_hash, file_path, char_count, was_edited, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_phase_artifacts(self, session_id: str, phase_number: int) -> list:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT pa.* FROM phase_artifacts pa
                   JOIN phase_gates pg ON pa.phase_gate_id = pg.id
                   WHERE pg.session_id = ? AND pg.phase_number = ?""",
                (session_id, phase_number),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_phase_artifact(self, phase_gate_id: int,
                              artifact_type: str, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [phase_gate_id, artifact_type]
        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE phase_artifacts SET {set_clause} WHERE phase_gate_id = ? AND artifact_type = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    # --- Artifact edits ---
    def save_artifact_edit(self, phase_artifact_id: int,
                           original_hash: str, edited_hash: str,
                           original_file_path: str, edited_by: str,
                           edit_summary: str = None):
        now = _now()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO artifact_edits
                   (phase_artifact_id, original_hash, edited_hash,
                    original_file_path, edited_by, edit_summary, edited_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (phase_artifact_id, original_hash, edited_hash,
                 original_file_path, edited_by, edit_summary, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_artifact_edits(self, session_id: str, phase_number: int) -> list:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT ae.* FROM artifact_edits ae
                   JOIN phase_artifacts pa ON ae.phase_artifact_id = pa.id
                   JOIN phase_gates pg ON pa.phase_gate_id = pg.id
                   WHERE pg.session_id = ? AND pg.phase_number = ?""",
                (session_id, phase_number),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Audit log ---
    def log_event(self, session_id: str, event_type: str,
                  phase_number: int = None, artifact_type: str = None,
                  actor: str = "system", detail: dict = None):
        now = _now()
        detail_json = json.dumps(detail) if detail else None
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO audit_log
                   (session_id, event_type, phase_number, artifact_type, actor, detail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, event_type, phase_number, artifact_type, actor, detail_json, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_audit_log(self, session_id: str, event_type: str = None,
                      limit: int = 200) -> list:
        conn = self._get_conn()
        try:
            if event_type:
                rows = conn.execute(
                    """SELECT * FROM audit_log
                       WHERE session_id = ? AND event_type = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (session_id, event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM audit_log
                       WHERE session_id = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (session_id, limit),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Full session export ---
    def export_session(self, session_id: str) -> dict:
        """Returns everything for debugging/support."""
        session = self.get_session(session_id)
        if not session:
            return {}
        return {
            "session": session,
            "questionnaire": self.get_questionnaire(session_id),
            "documents": self.get_documents(session_id),
            "phase_gates": self.get_all_phase_gates(session_id),
            "audit_log": self.get_audit_log(session_id, limit=500),
        }


def _now() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id                TEXT PRIMARY KEY,
    flow_type         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'intake',
    questionnaire_ver TEXT,
    input_dir         TEXT,
    output_dir        TEXT,
    snapshot_base_dir TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question_id     TEXT NOT NULL,
    question_text   TEXT NOT NULL,
    answer          TEXT NOT NULL,
    mapping         TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(session_id, question_id)
);

CREATE TABLE IF NOT EXISTS session_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_size       INTEGER,
    file_type       TEXT,
    content_hash    TEXT,
    uploaded_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phase_gates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    phase_number        INTEGER NOT NULL CHECK (phase_number IN (1, 2, 3)),
    phase_name          TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    overall_progress    INTEGER DEFAULT 0,
    started_at          TEXT,
    generated_at        TEXT,
    completed_at        TEXT,
    approved_by         TEXT,
    approval_notes      TEXT,
    rejection_feedback  TEXT,
    rejection_count     INTEGER DEFAULT 0,
    snapshot_dir        TEXT,
    UNIQUE(session_id, phase_number)
);

CREATE TABLE IF NOT EXISTS generation_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_gate_id   INTEGER NOT NULL REFERENCES phase_gates(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    progress_pct    INTEGER DEFAULT 0,
    message         TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    char_count      INTEGER,
    generation_ms   INTEGER,
    error_message   TEXT,
    UNIQUE(phase_gate_id, artifact_type)
);

CREATE TABLE IF NOT EXISTS phase_artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_gate_id   INTEGER NOT NULL REFERENCES phase_gates(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    char_count      INTEGER,
    was_edited      BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL,
    UNIQUE(phase_gate_id, artifact_type)
);

CREATE TABLE IF NOT EXISTS artifact_edits (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_artifact_id   INTEGER NOT NULL REFERENCES phase_artifacts(id) ON DELETE CASCADE,
    original_hash       TEXT NOT NULL,
    edited_hash         TEXT NOT NULL,
    original_file_path  TEXT NOT NULL,
    edited_by           TEXT NOT NULL,
    edit_summary        TEXT,
    edited_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    phase_number    INTEGER,
    artifact_type   TEXT,
    actor           TEXT,
    detail          TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type, created_at);
"""
