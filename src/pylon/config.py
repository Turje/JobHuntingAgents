"""
YAML + .env config loader for Pylon.
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


# Anthropic
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", _settings.get("claude_model", "claude-sonnet-4-6"))

# Retry
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", _limits.get("max_retries", 3)))
RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", _limits.get("retry_base_delay", 1.0)))

# Pipeline
MAX_COMPANIES_PER_SEARCH: int = int(
    os.getenv("MAX_COMPANIES_PER_SEARCH", _settings.get("max_companies_per_search", 15))
)
MAX_OUTREACH_PER_DAY: int = int(
    os.getenv("MAX_OUTREACH_PER_DAY", _settings.get("max_outreach_per_day", 10))
)

# Server
HOST: str = os.getenv("HOST", _settings.get("host", "127.0.0.1"))
PORT: int = int(os.getenv("PORT", _settings.get("port", 8000)))

# Gmail (optional)
GMAIL_CREDENTIALS_PATH: str = os.getenv("GMAIL_CREDENTIALS_PATH", "")
GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "")


def validate_required_keys() -> None:
    """Call once at startup to verify required env vars."""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is required but not set. Add it to your .env file."
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
