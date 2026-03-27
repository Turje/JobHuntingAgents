# JobHuntingAgents — Multi-Agent Job Hunting Platform

## Architecture
- **Router** orchestration with 7-priority intent classification
- **Actor-Critic** workflows for search planning + outreach review (max 3 cycles)
- **Swarm** parallel exploration for multi-company research
- **Pydantic** models for all data contracts (all in `src/pylon/models.py`)
- **SQLite** persistence with WAL mode via aiosqlite
- **FastAPI + WebSocket** for real-time pipeline progress
- **Stable-anchor memory** in `memory/` directory

## Conventions
- All Pydantic models live in `src/pylon/models.py` — no scattered model files
- Agent brain files (system prompts) go in `agents/*.md`
- YAML config in `config/` — never hardcode settings
- Every agent returns a `RouterContract` for accountability
- Tests use `pytest` + `pytest-asyncio`, mocks for Claude API calls
- Error handling: agents return safe defaults, never raise to callers
- ClaudeClient wrapper handles retry + backoff for all LLM calls

## Pipeline Flow
```
User query → Router → Intent → AC Planning → FullSearchPipeline
  → Discovery → Research → Skills → Contact → Resume → Outreach → Excel → [Gmail]
```

## Commands
- `pytest tests/ -v` — run all tests
- `uvicorn pylon.main:app --reload` — start dev server
- `ruff check src/ tests/` — lint

## Project Layout
- `src/pylon/` — all source code (hatch package)
- `agents/` — brain files (markdown system prompts)
- `config/` — YAML configuration
- `knowledge/` — domain knowledge (industries, templates, resume)
- `memory/` — stable-anchor operational memory
- `workflows/` — workflow documentation
- `docs/` — GitHub Pages site
- `tests/` — pytest test suite
