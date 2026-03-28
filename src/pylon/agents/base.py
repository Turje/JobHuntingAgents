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
from pylon.models import PipelineContext, RouterContract, SearchMode


# Mode-specific prompt hints per agent type
_DS_ML_HINTS: dict[str, str] = {
    "discovery": (
        "\n\n[SEARCH MODE: DS/ML] Focus on companies with data science, machine learning, "
        "or AI roles. These can be ANY industry — airlines, logistics, healthcare, finance, "
        "retail, manufacturing, sports, etc. — not just tech companies. Look for companies "
        "that have data teams, ML engineering groups, or AI initiatives."
    ),
    "research": (
        "\n\n[SEARCH MODE: DS/ML] Research each company's data science and ML capabilities. "
        "Focus on: ML/AI teams, data infrastructure, model deployment practices, data science "
        "use cases, and how they leverage data for business decisions. Search for "
        '"[company] data science ML team careers" and similar queries.'
    ),
    "skills": (
        "\n\n[SEARCH MODE: DS/ML] Emphasize ML frameworks and data tools: PyTorch, TensorFlow, "
        "scikit-learn, Spark, pandas, Airflow, MLflow, Kubeflow, Databricks, dbt, SQL, "
        "feature stores, vector databases, LLM tooling, and cloud ML services (SageMaker, "
        "Vertex AI, Azure ML)."
    ),
    "tools": (
        "\n\n[SEARCH MODE: DS/ML] Suggest ML-specific buildable projects: feature stores, "
        "ML pipelines, model monitoring dashboards, A/B testing frameworks, recommendation "
        "engines, NLP tools, data quality monitors, ML model registries, automated EDA tools, "
        "or domain-specific ML applications relevant to the company's industry."
    ),
    "contact": (
        "\n\n[SEARCH MODE: DS/ML] Look for data science and ML leadership: Head of Data Science, "
        "ML Engineering Manager, Chief Data Officer, VP of Analytics, Director of AI, "
        "Principal Data Scientist, Head of ML Platform."
    ),
    "resume": (
        "\n\n[SEARCH MODE: DS/ML] Emphasize ML/DS skills and projects: model development, "
        "data pipelines, experimentation, production ML systems, statistical analysis, "
        "deep learning, NLP, computer vision, and relevant ML frameworks."
    ),
    "outreach": (
        "\n\n[SEARCH MODE: DS/ML] Pitch data science and ML expertise. Reference specific "
        "ML use cases the company works on, mention relevant frameworks and tools, and "
        "highlight experience with production ML systems or data-driven decision making."
    ),
}


def get_mode_hint(agent_name: str, context: PipelineContext) -> str:
    """Return mode-specific prompt hint for the agent, or empty string for general mode."""
    if context.search_mode == SearchMode.DS_ML:
        return _DS_ML_HINTS.get(agent_name, "")
    return ""


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
