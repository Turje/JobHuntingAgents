"""
SQLite persistence for CastNet sessions, companies, contacts, and drafts.
Uses aiosqlite with WAL mode for async access.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "pylon.db"


class SessionStore:
    """Async SQLite store for pipeline sessions and results."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(db_path or _DEFAULT_DB)

    async def initialize(self) -> None:
        """Create database and tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executescript(_SCHEMA)
            # Migrate: add excel_path to sessions if missing
            try:
                await db.execute("ALTER TABLE sessions ADD COLUMN excel_path TEXT DEFAULT ''")
            except Exception:
                pass  # column already exists
            await db.commit()

    async def create_session(self, query: str, run_id: str | None = None) -> str:
        """Create a new pipeline session. Returns the session run_id."""
        rid = run_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (run_id, query, created_at, status) VALUES (?, ?, ?, ?)",
                (rid, query, now, "running"),
            )
            await db.commit()
        return rid

    async def end_session(self, run_id: str, status: str = "completed") -> None:
        """Mark a session as completed or failed."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET status = ?, ended_at = ? WHERE run_id = ?",
                (status, now, run_id),
            )
            await db.commit()

    async def get_session(self, run_id: str) -> Optional[dict[str, Any]]:
        """Get a session by run_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE run_id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def save_companies(self, run_id: str, companies: list[dict[str, Any]]) -> None:
        """Save discovered companies for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for c in companies:
                await db.execute(
                    "INSERT INTO companies (run_id, name, domain, website, confidence, data_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        c.get("name", ""),
                        c.get("domain", ""),
                        c.get("website", ""),
                        c.get("confidence", 0.0),
                        json.dumps(c),
                    ),
                )
            await db.commit()

    async def save_contacts(self, run_id: str, contacts: list[dict[str, Any]]) -> None:
        """Save contact information for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for ct in contacts:
                await db.execute(
                    "INSERT INTO contacts (run_id, company_name, name, title, email, linkedin_url, data_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        ct.get("company_name", ""),
                        ct.get("name", ""),
                        ct.get("title", ""),
                        ct.get("email", ""),
                        ct.get("linkedin_url", ""),
                        json.dumps(ct),
                    ),
                )
            await db.commit()

    async def save_drafts(self, run_id: str, drafts: list[dict[str, Any]]) -> None:
        """Save outreach drafts for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for d in drafts:
                await db.execute(
                    "INSERT INTO drafts (run_id, company_name, contact_name, subject, body, status, data_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        d.get("company_name", ""),
                        d.get("contact_name", ""),
                        d.get("subject", ""),
                        d.get("body", ""),
                        d.get("status", "draft"),
                        json.dumps(d),
                    ),
                )
            await db.commit()

    async def get_companies(self, run_id: str) -> list[dict[str, Any]]:
        """Get all companies for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM companies WHERE run_id = ? ORDER BY confidence DESC", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def get_drafts(self, run_id: str) -> list[dict[str, Any]]:
        """Get all drafts for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM drafts WHERE run_id = ?", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def update_draft_status(self, draft_id: int, status: str, gmail_draft_id: str = "") -> None:
        """Update a draft's status and optional Gmail draft ID."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE drafts SET status = ?, gmail_draft_id = ? WHERE id = ?",
                (status, gmail_draft_id, draft_id),
            )
            await db.commit()

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions ordered by created_at DESC."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC"
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def save_profiles(self, run_id: str, profiles: list[dict[str, Any]]) -> None:
        """Save company profiles for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for p in profiles:
                await db.execute(
                    "INSERT INTO profiles (run_id, company_name, data_json) VALUES (?, ?, ?)",
                    (run_id, p.get("company_name", ""), json.dumps(p)),
                )
            await db.commit()

    async def get_profiles(self, run_id: str) -> list[dict[str, Any]]:
        """Get all profiles for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM profiles WHERE run_id = ?", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def save_skills(self, run_id: str, skills: list[dict[str, Any]]) -> None:
        """Save skills analyses for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for s in skills:
                await db.execute(
                    "INSERT INTO skills (run_id, company_name, alignment_score, data_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        s.get("company_name", ""),
                        s.get("alignment_score", 0.0),
                        json.dumps(s),
                    ),
                )
            await db.commit()

    async def get_skills(self, run_id: str) -> list[dict[str, Any]]:
        """Get all skills analyses for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM skills WHERE run_id = ? ORDER BY alignment_score DESC",
                (run_id,),
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def save_resumes(self, run_id: str, resumes: list[dict[str, Any]]) -> None:
        """Save tailored resumes for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for r in resumes:
                await db.execute(
                    "INSERT INTO resumes (run_id, company_name, data_json) VALUES (?, ?, ?)",
                    (run_id, r.get("company_name", ""), json.dumps(r)),
                )
            await db.commit()

    async def get_resumes(self, run_id: str) -> list[dict[str, Any]]:
        """Get all resumes for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM resumes WHERE run_id = ?", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def get_contacts(self, run_id: str) -> list[dict[str, Any]]:
        """Get all contacts for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM contacts WHERE run_id = ?", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def save_excel_path(self, run_id: str, path: str) -> None:
        """Save the Excel export path for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET excel_path = ? WHERE run_id = ?",
                (path, run_id),
            )
            await db.commit()

    async def delete_session(self, run_id: str) -> bool:
        """Delete a session and all its related data. Returns True if found."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check session exists
            async with db.execute(
                "SELECT run_id FROM sessions WHERE run_id = ?", (run_id,)
            ) as cursor:
                if not await cursor.fetchone():
                    return False
            # Delete all related data
            for table in ("companies", "contacts", "drafts", "profiles", "skills", "resumes", "tool_suggestions", "events"):
                await db.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
            await db.execute("DELETE FROM sessions WHERE run_id = ?", (run_id,))
            await db.commit()
            return True

    async def save_tool_suggestions(self, run_id: str, suggestions: list[dict[str, Any]]) -> None:
        """Save tool suggestions for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            for s in suggestions:
                await db.execute(
                    "INSERT INTO tool_suggestions (run_id, company_name, tool_name, data_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        s.get("company_name", ""),
                        s.get("tool_name", ""),
                        json.dumps(s),
                    ),
                )
            await db.commit()

    async def get_tool_suggestions(self, run_id: str) -> list[dict[str, Any]]:
        """Get all tool suggestions for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tool_suggestions WHERE run_id = ?", (run_id,)
            ) as cursor:
                return [dict(row) async for row in cursor]

    async def save_uploaded_resume(self, filename: str, content_text: str, content_type: str) -> int:
        """Save an uploaded resume. Returns the row id."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO uploaded_resumes (filename, content_text, content_type, created_at) "
                "VALUES (?, ?, ?, ?)",
                (filename, content_text, content_type, now),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_uploaded_resume(self, resume_id: int) -> Optional[dict[str, Any]]:
        """Get a specific uploaded resume by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM uploaded_resumes WHERE id = ?", (resume_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_latest_uploaded_resume(self) -> Optional[dict[str, Any]]:
        """Get the most recently uploaded resume."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM uploaded_resumes ORDER BY created_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def record_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        """Record a pipeline event for audit trail."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO events (run_id, event_type, payload_json, created_at) "
                "VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(payload), now),
            )
            await db.commit()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    run_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    name TEXT NOT NULL,
    domain TEXT,
    website TEXT,
    confidence REAL DEFAULT 0.0,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    email TEXT,
    linkedin_url TEXT,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    contact_name TEXT,
    subject TEXT,
    body TEXT,
    status TEXT DEFAULT 'draft',
    gmail_draft_id TEXT,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    alignment_score REAL DEFAULT 0.0,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tool_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    company_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    data_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS uploaded_resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    content_text TEXT NOT NULL,
    content_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES sessions(run_id),
    event_type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_companies_run ON companies(run_id);
CREATE INDEX IF NOT EXISTS idx_contacts_run ON contacts(run_id);
CREATE INDEX IF NOT EXISTS idx_drafts_run ON drafts(run_id);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_profiles_run ON profiles(run_id);
CREATE INDEX IF NOT EXISTS idx_skills_run ON skills(run_id);
CREATE INDEX IF NOT EXISTS idx_resumes_run ON resumes(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_suggestions_run ON tool_suggestions(run_id);
"""
