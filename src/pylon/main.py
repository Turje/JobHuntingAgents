"""
FastAPI + WebSocket entry point for CastNet.
Provides REST endpoints for search pipeline and WebSocket for live progress.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from pathlib import Path

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
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
    _logger.info("CastNet started — store initialized")
    yield
    _logger.info("CastNet shutting down")


app = FastAPI(
    title="CastNet",
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
    from pylon.router import CastNetRouter
    return CastNetRouter()


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
            if ctx.tools:
                await _store.save_tool_suggestions(
                    run_id, [t.model_dump() for t in ctx.tools]
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


@app.get("/sessions/{run_id}/tool-suggestions")
async def get_tool_suggestions(run_id: str) -> JSONResponse:
    """Get tool suggestions for a session."""
    suggestions = await _store.get_tool_suggestions(run_id)
    return JSONResponse({"tool_suggestions": suggestions})


@app.post("/upload-resume")
async def upload_resume(file: UploadFile) -> JSONResponse:
    """Upload a resume (PDF or DOCX), extract text, and store it."""
    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    content_type = file.content_type or ""
    raw = await file.read()

    if file.filename.lower().endswith(".pdf") or "pdf" in content_type:
        text = _extract_pdf_text(raw)
    elif file.filename.lower().endswith(".docx") or "wordprocessing" in content_type:
        text = _extract_docx_text(raw)
    else:
        return JSONResponse(
            {"error": "Unsupported file type. Upload PDF or DOCX."}, status_code=400
        )

    if not text.strip():
        return JSONResponse({"error": "Could not extract text from file"}, status_code=400)

    resume_id = await _store.save_uploaded_resume(file.filename, text, content_type)
    return JSONResponse({
        "id": resume_id,
        "filename": file.filename,
        "content_text": text[:500],
        "length": len(text),
    })


@app.get("/uploaded-resume")
async def get_uploaded_resume() -> JSONResponse:
    """Get the most recently uploaded resume."""
    resume = await _store.get_latest_uploaded_resume()
    if not resume:
        return JSONResponse({"resume": None})
    return JSONResponse({"resume": resume})


@app.post("/sessions/{run_id}/update-resume-for-tool")
async def update_resume_for_tool(run_id: str, payload: dict[str, Any]) -> JSONResponse:
    """Re-tailor resume for a specific company + tool suggestion."""
    company_name = payload.get("company_name", "")
    tool_name = payload.get("tool_name", "")
    tool_description = payload.get("tool_description", "")

    if not company_name or not tool_name:
        return JSONResponse(
            {"error": "company_name and tool_name are required"}, status_code=400
        )

    # Load uploaded resume
    resume_data = await _store.get_latest_uploaded_resume()
    if not resume_data:
        return JSONResponse({"error": "No uploaded resume found"}, status_code=400)

    resume_text = resume_data.get("content_text", "")

    # Load company context
    profiles = await _store.get_profiles(run_id)
    skills = await _store.get_skills(run_id)

    profile_data = {}
    for p in profiles:
        pd = json.loads(p.get("data_json", "{}"))
        if pd.get("company_name") == company_name:
            profile_data = pd
            break

    skills_data = {}
    for s in skills:
        sd = json.loads(s.get("data_json", "{}"))
        if sd.get("company_name") == company_name:
            skills_data = sd
            break

    # Call ResumeAgent with tool-tailoring context
    try:
        from pylon.core.claude_client import ClaudeClient

        client = ClaudeClient(agent_name="resume_tailor")
        system_prompt = (
            "You are a resume tailoring expert. Given a user's resume text, a target company, "
            "and a specific tool/product they plan to build for that company, re-write the resume "
            "to emphasize skills and experience relevant to building that tool at that company.\n\n"
            "Return a JSON object with:\n"
            '- "company_name": the company name\n'
            '- "tailored_summary": a 2-3 sentence professional summary pitched around the tool\n'
            '- "emphasis_areas": list of skill areas to highlight\n'
            '- "highlighted_projects": list of relevant projects from the resume\n'
            '- "tailored_bullets": list of tailored bullet points\n'
            "Return ONLY the JSON object."
        )

        user_message = (
            f"Resume:\n{resume_text}\n\n"
            f"Target Company: {company_name}\n"
            f"Company Profile: {json.dumps(profile_data)}\n"
            f"Skills Data: {json.dumps(skills_data)}\n\n"
            f"Tool to Build: {tool_name}\n"
            f"Tool Description: {tool_description}\n\n"
            "Tailor this resume for someone who will build this tool at this company."
        )

        response = client.call(system_prompt=system_prompt, user_message=user_message)

        # Parse response
        try:
            # Strip markdown fences if present
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
            resume_version = json.loads(text)
        except json.JSONDecodeError:
            resume_version = {
                "company_name": company_name,
                "tailored_summary": response[:500],
                "emphasis_areas": [],
                "highlighted_projects": [],
                "tailored_bullets": [],
            }

        resume_version["company_name"] = company_name
        await _store.save_resumes(run_id, [resume_version])
        return JSONResponse({"status": "updated", "resume": resume_version})

    except Exception as exc:
        _logger.error("Resume tailoring for tool failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


def _extract_pdf_text(raw: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        import io
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as exc:
        _logger.warning("PDF extraction failed: %s", exc)
        return ""


def _extract_docx_text(raw: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        import io
        import docx
        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        _logger.warning("DOCX extraction failed: %s", exc)
        return ""


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
