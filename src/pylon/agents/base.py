"""
Abstract base classes for CastNet agents.
Two hierarchies: BaseSearchAgent (discovery, research) and BaseAnalysisAgent (skills, contact, resume, outreach).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pylon.config import DSPY_ENABLED
from pylon.models import PipelineContext, RouterContract


def _safe_parse_json(text: str, agent_name: str) -> list[dict[str, Any]]:
    """Parse LLM JSON response, handling markdown fences and truncation."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except (json.JSONDecodeError, ValueError):
        # Truncated JSON recovery: find all complete JSON objects in the array
        objects = []
        for m in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text):
            try:
                obj = json.loads(m.group())
                objects.append(obj)
            except (json.JSONDecodeError, ValueError):
                continue
        if objects:
            logging.getLogger(f"agent.{agent_name}").warning(
                "JSON truncated — recovered %d complete objects", len(objects)
            )
            return objects
        logging.getLogger(f"agent.{agent_name}").warning(
            "JSON parse failed, no recoverable objects"
        )
        return []


class BaseSearchAgent(ABC):
    """ABC for agents that search for and discover information (Discovery, Research)."""

    name: str  # Must be set by subclasses

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):
            if not hasattr(cls, "name") or cls.name is None:
                raise TypeError(
                    f"Concrete subclass {cls.__name__} must define class attribute 'name'"
                )

    @property
    def _use_dspy(self) -> bool:
        """Whether to use DSPy modules instead of direct ClaudeClient calls."""
        return DSPY_ENABLED

    @abstractmethod
    def run(self, context: PipelineContext) -> RouterContract:
        """
        Execute the agent's search task.
        Reads from context, writes results back to context, returns a RouterContract.
        """

    def _load_brain(self) -> str:
        """Load the agent's brain file (system prompt) from agents/<name>.md."""
        brain_path = Path(__file__).resolve().parent.parent.parent.parent / "agents" / f"{self.name}.md"
        if brain_path.exists():
            return brain_path.read_text()
        return f"You are the {self.name} agent for CastNet, a job-hunting platform."

    def _safe_parse_json(self, text: str) -> list[dict[str, Any]]:
        return _safe_parse_json(text, self.name)


class BaseAnalysisAgent(ABC):
    """ABC for agents that analyze existing data (Skills, Contact, Resume, Outreach)."""

    name: str  # Must be set by subclasses

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):
            if not hasattr(cls, "name") or cls.name is None:
                raise TypeError(
                    f"Concrete subclass {cls.__name__} must define class attribute 'name'"
                )

    @property
    def _use_dspy(self) -> bool:
        """Whether to use DSPy modules instead of direct ClaudeClient calls."""
        return DSPY_ENABLED

    @abstractmethod
    def run(self, context: PipelineContext) -> RouterContract:
        """
        Execute the agent's analysis task.
        Reads from context, writes results back to context, returns a RouterContract.
        """

    def _load_brain(self) -> str:
        """Load the agent's brain file (system prompt) from agents/<name>.md."""
        brain_path = Path(__file__).resolve().parent.parent.parent.parent / "agents" / f"{self.name}.md"
        if brain_path.exists():
            return brain_path.read_text()
        return f"You are the {self.name} agent for CastNet, a job-hunting platform."

    def _safe_parse_json(self, text: str) -> list[dict[str, Any]]:
        return _safe_parse_json(text, self.name)
