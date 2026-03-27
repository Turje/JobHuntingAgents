"""
FastAPI + WebSocket entry point for JobHuntingAgents.
Provides REST endpoints for search pipeline and WebSocket for live progress.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from pylon.config import DSPY_ENABLED, HOST, PORT
from pylon.store import SessionStore

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DASHBOARD_HTML = _PROJECT_ROOT / "docs" / "index.html"

logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
_logger = logging.getLogger("pylon.main")

_store = SessionStore()
_ws_connections: dict[str, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize store on startup."""
    await _store.initialize()
    _logger.info("JobHuntingAgents started — store initialized")
    yield
    _logger.info("JobHuntingAgents shutting down")


app = FastAPI(
    title="JobHuntingAgents",
    description="Multi-agent job hunting platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_router():
    """Lazy import to avoid ClaudeClient init at module level."""
    from pylon.router import JobHuntingAgentsRouter
    return JobHuntingAgentsRouter()


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "dspy_enabled": DSPY_ENABLED})


@app.get("/sessions")
async def list_sessions() -> JSONResponse:
    """List all sessions ordered by most recent first."""
    sessions = await _store.list_sessions()
    return JSONResponse({"sessions": sessions})


@app.post("/search")
async def start_search(payload: dict[str, Any]) -> JSONResponse:
    """
    Start a search pipeline.
    Body: {"query": "find football analytics companies"}
    Returns: {"run_id": "...", "status": "running"}
    """
    query = payload.get("query", "")
    if not query:
        return JSONResponse({"error": "query is required"}, status_code=400)

    run_id = await _store.create_session(query)

    async def _run_pipeline():
        try:
            router = _get_router()

            def on_progress(step: str, data: Any) -> None:
                asyncio.get_event_loop().call_soon_threadsafe(
                    _schedule_broadcast, run_id, step, data
                )

            ctx, contract = router.handle_intent(query, on_progress=on_progress)

            if ctx.candidates:
                await _store.save_companies(
                    run_id, [c.model_dump() for c in ctx.candidates]
                )
            if ctx.profiles:
                await _store.save_profiles(
                    run_id, [p.model_dump() for p in ctx.profiles]
                )
            if ctx.skills:
                await _store.save_skills(
                    run_id, [s.model_dump() for s in ctx.skills]
                )
            if ctx.contacts:
                await _store.save_contacts(
                    run_id, [c.model_dump() for c in ctx.contacts]
                )
            if ctx.resumes:
                await _store.save_resumes(
                    run_id, [r.model_dump() for r in ctx.resumes]
                )
            if ctx.drafts:
                await _store.save_drafts(
                    run_id, [d.model_dump() for d in ctx.drafts]
                )
            if ctx.excel_path:
                await _store.save_excel_path(run_id, ctx.excel_path)

            await _store.end_session(run_id, "completed")
            await _broadcast(run_id, "complete", contract.model_dump())

        except Exception as exc:
            _logger.error("Pipeline failed for %s: %s", run_id, exc)
            await _store.end_session(run_id, "failed")
            await _broadcast(run_id, "error", {"message": str(exc)})

    asyncio.create_task(_run_pipeline())

    return JSONResponse({"run_id": run_id, "status": "running"})


@app.get("/sessions/{run_id}")
async def get_session(run_id: str) -> JSONResponse:
    """Get session details."""
    session = await _store.get_session(run_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse(session)


@app.delete("/sessions/{run_id}")
async def delete_session(run_id: str) -> JSONResponse:
    """Delete a session and all its data."""
    deleted = await _store.delete_session(run_id)
    if not deleted:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse({"status": "deleted", "run_id": run_id})


@app.get("/sessions/{run_id}/companies")
async def get_companies(run_id: str) -> JSONResponse:
    """Get discovered companies for a session."""
    companies = await _store.get_companies(run_id)
    return JSONResponse({"companies": companies})


@app.get("/sessions/{run_id}/drafts")
async def get_drafts(run_id: str) -> JSONResponse:
    """Get outreach drafts for a session."""
    drafts = await _store.get_drafts(run_id)
    return JSONResponse({"drafts": drafts})


@app.post("/sessions/{run_id}/approve-draft/{draft_id}")
async def approve_draft(run_id: str, draft_id: int) -> JSONResponse:
    """Approve an outreach draft (user gate before Gmail)."""
    await _store.update_draft_status(draft_id, "approved")
    return JSONResponse({"status": "approved", "draft_id": draft_id})


@app.get("/sessions/{run_id}/contacts")
async def get_contacts(run_id: str) -> JSONResponse:
    """Get contacts for a session."""
    contacts = await _store.get_contacts(run_id)
    return JSONResponse({"contacts": contacts})


@app.get("/sessions/{run_id}/skills")
async def get_skills(run_id: str) -> JSONResponse:
    """Get skills analyses for a session."""
    skills = await _store.get_skills(run_id)
    return JSONResponse({"skills": skills})


@app.get("/sessions/{run_id}/profiles")
async def get_profiles(run_id: str) -> JSONResponse:
    """Get company research profiles for a session."""
    profiles = await _store.get_profiles(run_id)
    return JSONResponse({"profiles": profiles})


@app.get("/sessions/{run_id}/resumes")
async def get_resumes(run_id: str) -> JSONResponse:
    """Get tailored resumes for a session."""
    resumes = await _store.get_resumes(run_id)
    return JSONResponse({"resumes": resumes})


@app.get("/sessions/{run_id}/excel")
async def get_excel(run_id: str):
    """Download the Excel report for a session."""
    session = await _store.get_session(run_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    excel_path = session.get("excel_path", "")
    if not excel_path or not Path(excel_path).is_file():
        return JSONResponse({"error": "Excel file not available"}, status_code=404)
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(excel_path).name,
    )


# ---------------------------------------------------------------------------
# WebSocket for live progress
# ---------------------------------------------------------------------------


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket for live pipeline progress updates."""
    await websocket.accept()
    _ws_connections.setdefault(run_id, []).append(websocket)
    _logger.info("WebSocket connected for run_id=%s", run_id)

    try:
        while True:
            data = await websocket.receive_text()
            _logger.debug("WS received: %s", data[:100])
    except WebSocketDisconnect:
        _ws_connections.get(run_id, []).remove(websocket) if websocket in _ws_connections.get(run_id, []) else None
        _logger.info("WebSocket disconnected for run_id=%s", run_id)


async def _broadcast(run_id: str, event: str, data: Any) -> None:
    """Broadcast a message to all WebSocket connections for a run_id."""
    connections = _ws_connections.get(run_id, [])
    message = json.dumps({"event": event, "data": data})
    for ws in connections:
        try:
            await ws.send_text(message)
        except Exception:
            pass


def _schedule_broadcast(run_id: str, event: str, data: Any) -> None:
    """Schedule a broadcast from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(run_id, event, data))
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the operational dashboard."""
    return FileResponse(_DASHBOARD_HTML, media_type="text/html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pylon.main:app", host=HOST, port=PORT, reload=True)
