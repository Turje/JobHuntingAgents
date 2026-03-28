"""
FullSearchPipeline — orchestrates all agents through the search pipeline.
Discover → Research → Skills → Tools → Contact → Resume → Outreach → Excel → [Gmail]
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from pylon.agents.contact import ContactAgent
from pylon.agents.discovery import DiscoveryAgent
from pylon.agents.outreach import OutreachAgent
from pylon.agents.research import ResearchAgent
from pylon.agents.resume import ResumeAgent
from pylon.agents.skills import SkillsAgent
from pylon.agents.tools import ToolSuggestionsAgent
from pylon.config import DSPY_ENABLED, LLM_PROVIDER
from pylon.excel import ExcelManager
from pylon.models import ContractStatus, PipelineContext, RouterContract

_logger = logging.getLogger("pipeline")

# Gemini free tier: ~15 RPM — pause between LLM-calling steps
_GEMINI_STEP_DELAY = 5  # seconds


class FullSearchPipeline:
    """
    Runs the full search pipeline from discovery through outreach.
    Each stage is optional and controlled by SearchConfig.
    Progress callbacks are fired at each step for WebSocket updates.
    """

    def __init__(self) -> None:
        if DSPY_ENABLED:
            try:
                from pylon.dspy_.lm import configure_dspy
                configure_dspy()
                _logger.info("DSPy configured for pipeline")
            except Exception as exc:
                _logger.warning("DSPy configuration failed, falling back to Claude: %s", exc)

        self.discovery = DiscoveryAgent()
        self._research = ResearchAgent()
        self._skills = SkillsAgent()
        self._tools = ToolSuggestionsAgent()
        self._contact = ContactAgent()
        self._resume = ResumeAgent()
        self._outreach = OutreachAgent()
        self._excel = ExcelManager()

    def run(
        self,
        context: PipelineContext,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> RouterContract:
        """
        Execute the full pipeline.

        Args:
            context: PipelineContext with query and intent set
            on_progress: Optional callback(step_name, data) for live updates

        Returns:
            Final RouterContract summarizing the pipeline run.
        """
        steps_completed = 0
        total_issues = 0
        use_delay = LLM_PROVIDER == "gemini"

        def _notify(step: str, data: Any = None) -> None:
            if on_progress:
                on_progress(step, data)

        def _rate_limit_pause() -> None:
            """Pause between LLM steps to respect Gemini free-tier RPM limits."""
            if use_delay:
                _logger.info("Rate-limit pause (%ds) for Gemini free tier", _GEMINI_STEP_DELAY)
                time.sleep(_GEMINI_STEP_DELAY)

        # Step 1: Discovery
        _notify("discovery_start", {"query": context.query})
        _logger.info("Pipeline step 1: Discovery")
        contract = self.discovery.run(context)
        _notify("discovery_complete", {"count": len(context.candidates)})
        steps_completed += 1
        total_issues += contract.critical_issues

        if contract.blocking or not context.candidates:
            _logger.warning("Discovery blocked or empty, stopping pipeline")
            return contract

        # Step 2: Research (Layer 2)
        _rate_limit_pause()
        _notify("research_start", {"count": len(context.candidates)})
        _logger.info("Pipeline step 2: Research")
        rc = self._research.run(context)
        _notify("research_complete", {"count": len(context.profiles)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 3: Skills (Layer 2)
        _rate_limit_pause()
        _notify("skills_start", {"count": len(context.profiles)})
        _logger.info("Pipeline step 3: Skills Analysis")
        rc = self._skills.run(context)
        _notify("skills_complete", {"count": len(context.skills)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 4: Tool Suggestions (Layer 2)
        _rate_limit_pause()
        _notify("tools_start", {"count": len(context.profiles)})
        _logger.info("Pipeline step 4: Tool Suggestions")
        rc = self._tools.run(context)
        _notify("tools_complete", {"count": len(context.tools)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 5: Contact (Layer 3)
        _rate_limit_pause()
        _notify("contact_start", {"count": len(context.candidates)})
        _logger.info("Pipeline step 5: Contact Search")
        rc = self._contact.run(context)
        _notify("contact_complete", {"count": len(context.contacts)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 6: Resume (Layer 4)
        _rate_limit_pause()
        _notify("resume_start", {"count": len(context.candidates)})
        _logger.info("Pipeline step 6: Resume Tailoring")
        rc = self._resume.run(context)
        _notify("resume_complete", {"count": len(context.resumes)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 7: Outreach (Layer 4)
        _rate_limit_pause()
        _notify("outreach_start", {"count": len(context.contacts)})
        _logger.info("Pipeline step 7: Outreach Drafts")
        rc = self._outreach.run(context)
        _notify("outreach_complete", {"count": len(context.drafts)})
        steps_completed += 1
        total_issues += rc.critical_issues

        # Step 8: Excel Export (no LLM call, no delay needed)
        _notify("excel_start", {})
        _logger.info("Pipeline step 8: Excel Export")
        context.excel_path = self._excel.export(context)
        _notify("excel_complete", {"path": context.excel_path})
        steps_completed += 1

        _notify("pipeline_complete", {"steps": steps_completed, "issues": total_issues})

        return RouterContract(
            status=ContractStatus.EXECUTED,
            confidence=max(0.0, 90.0 - total_issues * 10.0),
            critical_issues=total_issues,
            blocking=False,
            kb_update_notes=f"Pipeline completed {steps_completed} steps for: {context.query[:50]}",
        )
