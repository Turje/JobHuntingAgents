"""Tests for src/pylon/store.py — SQLite persistence."""

import tempfile
from pathlib import Path

import pytest

from pylon.store import SessionStore


@pytest.fixture
async def store(tmp_path):
    """Create a fresh SessionStore with a temp database."""
    db_path = tmp_path / "test.db"
    s = SessionStore(db_path=db_path)
    await s.initialize()
    return s


class TestSessionStore:
    async def test_initialize_creates_db(self, tmp_path):
        db_path = tmp_path / "init_test.db"
        store = SessionStore(db_path=db_path)
        await store.initialize()
        assert db_path.exists()

    async def test_create_and_get_session(self, store):
        run_id = await store.create_session("find football companies")
        session = await store.get_session(run_id)
        assert session is not None
        assert session["query"] == "find football companies"
        assert session["status"] == "running"

    async def test_end_session(self, store):
        run_id = await store.create_session("test query")
        await store.end_session(run_id, status="completed")
        session = await store.get_session(run_id)
        assert session["status"] == "completed"
        assert session["ended_at"] is not None

    async def test_save_and_get_companies(self, store):
        run_id = await store.create_session("test")
        companies = [
            {"name": "StatsBomb", "domain": "sports_tech", "website": "https://statsbomb.com", "confidence": 0.9},
            {"name": "Opta", "domain": "sports_tech", "website": "https://opta.com", "confidence": 0.8},
        ]
        await store.save_companies(run_id, companies)
        result = await store.get_companies(run_id)
        assert len(result) == 2
        assert result[0]["name"] == "StatsBomb"  # sorted by confidence DESC

    async def test_save_contacts(self, store):
        run_id = await store.create_session("test")
        contacts = [
            {"company_name": "TestCo", "name": "Jane", "title": "CTO", "email": "jane@test.com"},
        ]
        await store.save_contacts(run_id, contacts)

    async def test_save_and_get_drafts(self, store):
        run_id = await store.create_session("test")
        drafts = [
            {"company_name": "TestCo", "contact_name": "Jane", "subject": "Hello", "body": "Hi there"},
        ]
        await store.save_drafts(run_id, drafts)
        result = await store.get_drafts(run_id)
        assert len(result) == 1
        assert result[0]["subject"] == "Hello"

    async def test_update_draft_status(self, store):
        run_id = await store.create_session("test")
        await store.save_drafts(run_id, [{"company_name": "X", "subject": "Hi", "body": "Hey"}])
        drafts = await store.get_drafts(run_id)
        draft_id = drafts[0]["id"]
        await store.update_draft_status(draft_id, "sent", "gmail_abc123")

    async def test_record_event(self, store):
        run_id = await store.create_session("test")
        await store.record_event(run_id, "discovery_complete", {"count": 10})

    async def test_get_nonexistent_session(self, store):
        result = await store.get_session("nonexistent-id")
        assert result is None
