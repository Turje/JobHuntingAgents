"""
DSPy LM configuration — singleton that wraps Anthropic via DSPy.
"""

from __future__ import annotations

import logging
from typing import Optional

import dspy

from pylon.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_logger = logging.getLogger("dspy_.lm")
_lm: Optional[dspy.LM] = None


def get_lm() -> dspy.LM:
    """Return a singleton DSPy LM backed by the Anthropic Claude model."""
    global _lm
    if _lm is None:
        if not ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is required for DSPy LM but not set."
            )
        model_id = f"anthropic/{CLAUDE_MODEL}"
        _logger.info("Creating DSPy LM: %s", model_id)
        _lm = dspy.LM(model_id, api_key=ANTHROPIC_API_KEY)
    return _lm


def configure_dspy() -> None:
    """Configure DSPy to use the Anthropic LM globally."""
    lm = get_lm()
    dspy.configure(lm=lm)
    _logger.info("DSPy configured with %s", lm.model)


def reset_lm() -> None:
    """Reset singleton — mainly for tests."""
    global _lm
    _lm = None
