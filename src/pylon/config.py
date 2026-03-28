"""
YAML + .env config loader for CastNet.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML file from the config directory."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Settings (env vars with YAML defaults)
# ---------------------------------------------------------------------------

_settings = _load_yaml("settings.yaml")
_limits = _load_yaml("limits.yaml")


# LLM Provider: "gemini" or "anthropic"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", _settings.get("llm_provider", "gemini"))

# Google Gemini
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", _settings.get("gemini_model", "gemini-2.0-flash"))

# Anthropic (fallback / optional)
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", _settings.get("claude_model", "claude-sonnet-4-6"))

# Retry
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", _limits.get("max_retries", 3)))
RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", _limits.get("retry_base_delay", 1.0)))

# Pipeline
MAX_COMPANIES_PER_SEARCH: int = int(
    os.getenv("MAX_COMPANIES_PER_SEARCH", _settings.get("max_companies_per_search", 30))
)
MAX_OUTREACH_PER_DAY: int = int(
    os.getenv("MAX_OUTREACH_PER_DAY", _settings.get("max_outreach_per_day", 10))
)

# Server
HOST: str = os.getenv("HOST", _settings.get("host", "127.0.0.1"))
PORT: int = int(os.getenv("PORT", _settings.get("port", 8000)))

# Serper.dev (primary — full Google web search)
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

# Google Custom Search (fallback when Serper credits exhausted)
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")

# Gmail (optional)
GMAIL_CREDENTIALS_PATH: str = os.getenv("GMAIL_CREDENTIALS_PATH", "")
GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "")

# DSPy (optional — for auto-optimizable prompt modules)
DSPY_ENABLED: bool = os.getenv("DSPY_ENABLED", "false").lower() in ("true", "1", "yes")
DSPY_OPTIMIZED_PATH: str = os.getenv("DSPY_OPTIMIZED_PATH", "")


def validate_required_keys() -> None:
    """Call once at startup to verify required env vars."""
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        raise EnvironmentError(
            "GEMINI_API_KEY is required when LLM_PROVIDER=gemini. Add it to your .env file."
        )
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. Add it to your .env file."
        )


def load_compliance() -> dict[str, Any]:
    """Load compliance/default.yaml for rate limits, GDPR, etiquette rules."""
    return _load_yaml("compliance/default.yaml")


def load_industry(name: str) -> dict[str, Any]:
    """Load a knowledge/industries/<name>.yaml file."""
    path = _PROJECT_ROOT / "knowledge" / "industries" / f"{name}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}
