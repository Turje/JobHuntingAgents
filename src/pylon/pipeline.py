"""
FullSearchPipeline — orchestrates all agents through the search pipeline.
Discover → Research → Skills → Contact → Resume → Outreach → Excel → [Gmail]
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from pylon.agents.discovery import DiscoveryAgent
from pylon.config import DSPY_ENABLED
from pylon.models import ContractStatus, PipelineContext, RouterContract

_logger = logging.getLogger("pipeline")


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
        # Layer 2+ agents are lazily imported when needed
        self._research = None
        self._skills = None
        self._contact = None
        self._resume = None
        self._outreach = None
        self._excel = None

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

        def _notify(step: str, data: Any = None) -> None:
            if on_progress:
                on_progress(step, data)

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
        if self._research:
            _notify("research_start", {"count": len(context.candidates)})
            _logger.info("Pipeline step 2: Research")
            rc = self._research.run(context)
            _notify("research_complete", {"count": len(context.profiles)})
            steps_completed += 1
            total_issues += rc.critical_issues

        # Step 3: Skills (Layer 2)
        if self._skills:
            _notify("skills_start", {"count": len(context.profiles)})
            _logger.info("Pipeline step 3: Skills Analysis")
            rc = self._skills.run(context)
            _notify("skills_complete", {"count": len(context.skills)})
            steps_completed += 1
            total_issues += rc.critical_issues

        # Step 4: Contact (Layer 3)
        if self._contact:
            _notify("contact_start", {"count": len(context.candidates)})
            _logger.info("Pipeline step 4: Contact Search")
            rc = self._contact.run(context)
            _notify("contact_complete", {"count": len(context.contacts)})
            steps_completed += 1
            total_issues += rc.critical_issues

        # Step 5: Resume (Layer 4)
        if self._resume:
            _notify("resume_start", {"count": len(context.candidates)})
            _logger.info("Pipeline step 5: Resume Tailoring")
            rc = self._resume.run(context)
            _notify("resume_complete", {"count": len(context.resumes)})
            steps_completed += 1
            total_issues += rc.critical_issues

        # Step 6: Outreach (Layer 4)
        if self._outreach:
            _notify("outreach_start", {"count": len(context.contacts)})
            _logger.info("Pipeline step 6: Outreach Drafts")
            rc = self._outreach.run(context)
            _notify("outreach_complete", {"count": len(context.drafts)})
            steps_completed += 1
            total_issues += rc.critical_issues

        # Step 7: Excel Export (Layer 3)
        if self._excel:
            _notify("excel_start", {})
            _logger.info("Pipeline step 7: Excel Export")
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
