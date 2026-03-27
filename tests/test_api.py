"""Tests for src/pylon/main.py — FastAPI REST endpoints."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from pylon.store import SessionStore


@pytest.fixture
async def client(tmp_path):
    """Create a test client with a fresh database."""
    db_path = tmp_path / "test_api.db"
    store = SessionStore(db_path=db_path)
    await store.initialize()

    with patch("pylon.main._store", store):
        from pylon.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, store


class TestAPI:
    async def test_health(self, client):
        ac, _ = client
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "dspy_enabled" in data

    async def test_list_sessions_empty(self, client):
        ac, _ = client
        resp = await ac.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}

    async def test_list_sessions_with_data(self, client):
        ac, store = client
        await store.create_session("query one", run_id="r1")
        await store.create_session("query two", run_id="r2")
        resp = await ac.get("/sessions")
        data = resp.json()
        assert len(data["sessions"]) == 2

    async def test_get_contacts(self, client):
        ac, store = client
        run_id = await store.create_session("test")
        await store.save_contacts(run_id, [
            {"company_name": "Acme", "name": "Alice", "title": "CTO", "email": "a@acme.com"},
        ])
        resp = await ac.get(f"/sessions/{run_id}/contacts")
        assert resp.status_code == 200
        assert len(resp.json()["contacts"]) == 1

    async def test_get_skills(self, client):
        ac, store = client
        run_id = await store.create_session("test")
        await store.save_skills(run_id, [
            {"company_name": "Acme", "alignment_score": 0.85},
        ])
        resp = await ac.get(f"/sessions/{run_id}/skills")
        assert resp.status_code == 200
        assert len(resp.json()["skills"]) == 1

    async def test_get_resumes(self, client):
        ac, store = client
        run_id = await store.create_session("test")
        await store.save_resumes(run_id, [
            {"company_name": "Acme", "tailored_summary": "ML expert"},
        ])
        resp = await ac.get(f"/sessions/{run_id}/resumes")
        assert resp.status_code == 200
        assert len(resp.json()["resumes"]) == 1

    async def test_get_excel_not_found(self, client):
        ac, store = client
        run_id = await store.create_session("test")
        resp = await ac.get(f"/sessions/{run_id}/excel")
        assert resp.status_code == 404

    async def test_get_excel_download(self, client, tmp_path):
        ac, store = client
        run_id = await store.create_session("test")
        excel_file = tmp_path / "report.xlsx"
        excel_file.write_bytes(b"fake xlsx content")
        await store.save_excel_path(run_id, str(excel_file))
        resp = await ac.get(f"/sessions/{run_id}/excel")
        assert resp.status_code == 200
        assert b"fake xlsx content" in resp.content
