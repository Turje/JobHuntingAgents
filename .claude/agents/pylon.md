# Pylon -- Claude Code Orchestrator

## Project

**Pylon** is a multi-agent job-hunting platform. It uses Claude as the LLM backbone to orchestrate a pipeline of specialized agents (Discovery, Research, Skills, Contact, Resume, Outreach) that automate company research, skill-gap analysis, and personalized cold outreach for job seekers.

- **Repo root:** The working directory is the Pylon project root.
- **Python:** >=3.10, managed via hatch.
- **LLM:** Anthropic Claude via the `anthropic` SDK, wrapped in `src/pylon/core/claude_client.py`.

---

## Key Conventions

### Models
All Pydantic models live in `src/pylon/models.py`. This is the single source of truth. Never create model files elsewhere. When adding a new data structure, add it to this file under the appropriate section header.

### Brain Files
Agent system prompts (brain files) live in `agents/*.md`. Each agent has one brain file that defines its role, input/output contract, and rules. These are loaded at runtime and passed as the `system` parameter to Claude API calls.

### Configuration
YAML config files go in `config/`. Never hardcode settings (API keys, thresholds, limits) in Python source. Use `src/pylon/config.py` to load and validate config.

### Knowledge Base
Domain knowledge (industry info, email templates, resume data) lives in `knowledge/`. Agents read from this directory but never write to it directly -- knowledge updates go through `RouterContract.kb_update_notes`.

### Memory
Operational memory lives in `memory/`. This is the stable-anchor pattern -- persisted state across sessions.

---

## Project Layout

```
src/pylon/           -- All source code (hatch package)
  models.py          -- Every Pydantic model
  config.py          -- YAML config loader
  store.py           -- SQLite persistence (aiosqlite, WAL mode)
  knowledge.py       -- Knowledge base reader
  core/
    claude_client.py -- LLM wrapper with retry + backoff
    context.py       -- PipelineContext management
agents/              -- Brain files (markdown system prompts)
config/              -- YAML configuration files
knowledge/           -- Domain knowledge (industries, templates, resume)
memory/              -- Stable-anchor operational memory
workflows/           -- Workflow documentation
tests/               -- pytest test suite
docs/                -- GitHub Pages site
```

---

## Commands

- **Test:** `pytest tests/ -v`
- **Build/Install:** `pip install -e ".[dev]"`
- **Run dev server:** `uvicorn pylon.main:app --reload`
- **Lint:** `ruff check src/ tests/`

---

## Coding Standards

- All async code uses `asyncio`. Tests use `pytest-asyncio` with `asyncio_mode = "auto"`.
- Every agent must return a `RouterContract` for accountability.
- Error handling: agents return safe defaults and never raise exceptions to callers. Failures are captured in the `RouterContract` (status=BLOCKED or ESCALATE).
- The `ClaudeClient` wrapper in `core/claude_client.py` handles retry and exponential backoff for all LLM calls. Never call the Anthropic SDK directly from agent code.
- Use `structlog` for all logging. No print statements.
- Type hints on all function signatures. Ruff enforces style (line-length 100, target py310).
