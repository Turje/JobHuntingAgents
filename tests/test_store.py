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

    async def test_list_sessions(self, store):
        await store.create_session("query one", run_id="r1")
        await store.create_session("query two", run_id="r2")
        sessions = await store.list_sessions()
        assert len(sessions) == 2
        assert sessions[0]["run_id"] == "r2"  # most recent first

    async def test_save_and_get_profiles(self, store):
        run_id = await store.create_session("test")
        profiles = [
            {"company_name": "Acme", "r_and_d_approach": "agile"},
            {"company_name": "Beta", "r_and_d_approach": "waterfall"},
        ]
        await store.save_profiles(run_id, profiles)
        result = await store.get_profiles(run_id)
        assert len(result) == 2
        assert result[0]["company_name"] == "Acme"

    async def test_save_and_get_skills(self, store):
        run_id = await store.create_session("test")
        skills = [
            {"company_name": "Acme", "alignment_score": 0.9, "tools_used": ["python"]},
            {"company_name": "Beta", "alignment_score": 0.6, "tools_used": ["java"]},
        ]
        await store.save_skills(run_id, skills)
        result = await store.get_skills(run_id)
        assert len(result) == 2
        assert result[0]["alignment_score"] == 0.9  # sorted DESC

    async def test_save_and_get_resumes(self, store):
        run_id = await store.create_session("test")
        resumes = [{"company_name": "Acme", "tailored_summary": "Expert in ML"}]
        await store.save_resumes(run_id, resumes)
        result = await store.get_resumes(run_id)
        assert len(result) == 1
        assert result[0]["company_name"] == "Acme"

    async def test_get_contacts(self, store):
        run_id = await store.create_session("test")
        await store.save_contacts(run_id, [
            {"company_name": "Acme", "name": "Alice", "title": "VP Eng", "email": "a@acme.com"},
        ])
        result = await store.get_contacts(run_id)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    async def test_save_excel_path(self, store):
        run_id = await store.create_session("test")
        await store.save_excel_path(run_id, "/tmp/report.xlsx")
        session = await store.get_session(run_id)
        assert session["excel_path"] == "/tmp/report.xlsx"

    async def test_save_and_get_tool_suggestions(self, store):
        run_id = await store.create_session("test")
        suggestions = [
            {"company_name": "Acme", "tool_name": "Widget Builder", "description": "Builds widgets"},
            {"company_name": "Beta", "tool_name": "API Monitor", "description": "Monitors APIs"},
        ]
        await store.save_tool_suggestions(run_id, suggestions)
        result = await store.get_tool_suggestions(run_id)
        assert len(result) == 2
        assert result[0]["company_name"] == "Acme"
        assert result[0]["tool_name"] == "Widget Builder"

    async def test_save_and_get_uploaded_resume(self, store):
        resume_id = await store.save_uploaded_resume("resume.pdf", "John Doe ML Engineer", "application/pdf")
        assert resume_id is not None
        resume = await store.get_uploaded_resume(resume_id)
        assert resume is not None
        assert resume["filename"] == "resume.pdf"
        assert resume["content_text"] == "John Doe ML Engineer"

    async def test_get_latest_uploaded_resume(self, store):
        await store.save_uploaded_resume("old.pdf", "Old resume", "application/pdf")
        await store.save_uploaded_resume("new.pdf", "New resume", "application/pdf")
        latest = await store.get_latest_uploaded_resume()
        assert latest is not None
        assert latest["filename"] == "new.pdf"
