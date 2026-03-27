"""
PipelineContext wrapper — thin helper around the PipelineContext model.
"""

from __future__ import annotations

from pylon.models import PipelineContext


def new_context(query: str) -> PipelineContext:
    """Create a fresh PipelineContext for a new search pipeline run."""
    return PipelineContext.new(query=query)
