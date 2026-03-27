"""
DSPy Module wrappers — one per agent, wrapping TypedChainOfThought(Signature).
Each module optionally loads optimized state from DSPY_OPTIMIZED_PATH.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import dspy

from pylon.config import DSPY_OPTIMIZED_PATH
from pylon.dspy_.signatures import (
    AnalyzeSkills,
    CritiqueOutreach,
    CritiqueSearch,
    DiscoverCompanies,
    DraftOutreach,
    FindContacts,
    PlanSearch,
    ResearchCompanies,
    TailorResumes,
)

_logger = logging.getLogger("dspy_.modules")


def _load_state(module: dspy.Module, agent_name: str) -> dspy.Module:
    """Load optimized state if DSPY_OPTIMIZED_PATH is set and file exists."""
    if not DSPY_OPTIMIZED_PATH:
        return module
    state_path = Path(DSPY_OPTIMIZED_PATH) / f"{agent_name}.json"
    if state_path.exists():
        _logger.info("Loading optimized state for %s from %s", agent_name, state_path)
        module.load(str(state_path))
    return module


class DiscoveryModule(dspy.Module):
    """DSPy module for company discovery."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(DiscoverCompanies)
        _load_state(self, "discovery")

    def forward(
        self,
        query: str,
        domain_hint: str = "",
        web_context: str = "",
        max_companies: int = 15,
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            domain_hint=domain_hint,
            web_context=web_context,
            max_companies=max_companies,
        )


class ResearchModule(dspy.Module):
    """DSPy module for company research."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(ResearchCompanies)
        _load_state(self, "research")

    def forward(
        self,
        query: str,
        companies_json: str,
        web_context: str = "",
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            companies_json=companies_json,
            web_context=web_context,
        )


class SkillsModule(dspy.Module):
    """DSPy module for skills analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(AnalyzeSkills)
        _load_state(self, "skills")

    def forward(
        self,
        query: str,
        profiles_json: str,
        web_context: str = "",
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            profiles_json=profiles_json,
            web_context=web_context,
        )


class ContactModule(dspy.Module):
    """DSPy module for finding contacts."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(FindContacts)
        _load_state(self, "contact")

    def forward(
        self,
        query: str,
        companies_json: str,
        web_context: str = "",
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            companies_json=companies_json,
            web_context=web_context,
        )


class ResumeModule(dspy.Module):
    """DSPy module for resume tailoring."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(TailorResumes)
        _load_state(self, "resume")

    def forward(
        self,
        query: str,
        companies_json: str,
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            companies_json=companies_json,
        )


class OutreachModule(dspy.Module):
    """DSPy module for outreach email drafting."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(DraftOutreach)
        _load_state(self, "outreach")

    def forward(
        self,
        query: str,
        contacts_json: str,
    ) -> dspy.Prediction:
        return self.predict(
            query=query,
            contacts_json=contacts_json,
        )


# ---------------------------------------------------------------------------
# AC modules
# ---------------------------------------------------------------------------


class PlanSearchModule(dspy.Module):
    """DSPy module for search planning (Actor)."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(PlanSearch)
        _load_state(self, "plan_search")

    def forward(self, task: str, feedback: str = "") -> dspy.Prediction:
        return self.predict(task=task, feedback=feedback)


class CritiqueSearchModule(dspy.Module):
    """DSPy module for search plan critique."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(CritiqueSearch)
        _load_state(self, "critique_search")

    def forward(self, task: str, plan: str) -> dspy.Prediction:
        return self.predict(task=task, plan=plan)


class CritiqueOutreachModule(dspy.Module):
    """DSPy module for outreach critique."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(CritiqueOutreach)
        _load_state(self, "critique_outreach")

    def forward(self, context: str, draft: str) -> dspy.Prediction:
        return self.predict(context=context, draft=draft)
