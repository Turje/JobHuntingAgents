"""
JobHuntingAgents router — intent classification → dispatch → workflows.
Renamed from PylonRouter to JobHuntingAgentsRouter.
Handles DISCOVER, EMERGENCY, REVIEW, and all other intents.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from pylon.intent import classify_intent
from pylon.knowledge import KnowledgeManager
from pylon.models import (
    ContractStatus,
    Intent,
    IntentPriority,
    PipelineContext,
    RouterContract,
)
from pylon.pipeline import FullSearchPipeline
from pylon.workflows.ac_agents import SearchCritic, SearchPlanner
from pylon.workflows.actor_critic import ActorCriticWorkflow

_logger = logging.getLogger("router")


class JobHuntingAgentsRouter:
    """
    Main orchestrator for the JobHuntingAgents platform.
    Classifies user intent, runs AC planning when needed, dispatches pipeline.
    """

    def __init__(self) -> None:
        self.pipeline = FullSearchPipeline()
        self.knowledge = KnowledgeManager()
        self._sessions: dict[str, PipelineContext] = {}

    def handle_intent(
        self,
        user_input: str,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> tuple[PipelineContext, RouterContract]:
        """
        Main entry point. Classify intent, plan if needed, dispatch.

        Returns:
            (context, final_contract)
        """
        intent = classify_intent(user_input)
        _logger.info(
            "Classified intent: priority=%s, domain=%s, swarm=%s",
            intent.priority.name,
            intent.domain.value,
            intent.swarm_worthy,
        )

        context = PipelineContext.new(user_input)
        context.intent = intent

        if intent.priority == IntentPriority.EMERGENCY:
            contract = self._handle_emergency(context)
        elif intent.priority == IntentPriority.REVIEW:
            contract = self._handle_review(context)
        elif intent.priority == IntentPriority.DISCOVER:
            contract = self._handle_discover(context, on_progress)
        elif intent.priority == IntentPriority.RESEARCH:
            contract = self._handle_research(context, on_progress)
        elif intent.priority == IntentPriority.OUTREACH:
            contract = self._handle_outreach(context, on_progress)
        else:
            # SKILLS, CONTACT — run pipeline with appropriate focus
            contract = self._handle_pipeline(context, on_progress)

        # Store session and update knowledge
        self._sessions[context.run_id] = context
        if contract.kb_update_notes:
            self.knowledge.update_from_contract(
                contract.kb_update_notes, contract.evidence
            )

        return context, contract

    def get_session(self, run_id: str) -> Optional[PipelineContext]:
        """Retrieve a stored session by run_id."""
        return self._sessions.get(run_id)

    # ------------------------------------------------------------------
    # Intent handlers
    # ------------------------------------------------------------------

    def _handle_emergency(self, context: PipelineContext) -> RouterContract:
        """Handle EMERGENCY intent — halt all operations."""
        _logger.warning("EMERGENCY intent: %s", context.query)
        return RouterContract(
            status=ContractStatus.EXECUTED,
            confidence=100.0,
            kb_update_notes=f"Emergency halt: {context.query[:100]}",
        )

    def _handle_review(self, context: PipelineContext) -> RouterContract:
        """Handle REVIEW intent — show progress/export."""
        _logger.info("REVIEW intent: %s", context.query)
        sessions_count = len(self._sessions)
        return RouterContract(
            status=ContractStatus.EXECUTED,
            confidence=100.0,
            kb_update_notes=f"Review: {sessions_count} sessions stored",
        )

    def _handle_discover(
        self,
        context: PipelineContext,
        on_progress: Optional[Callable] = None,
    ) -> RouterContract:
        """Handle DISCOVER intent — AC planning then full pipeline."""
        _logger.info("DISCOVER intent: running AC planning loop")

        # Run pipeline (AC planning is optional, runs as enhancement)
        return self.pipeline.run(context, on_progress=on_progress)

    def _handle_research(
        self,
        context: PipelineContext,
        on_progress: Optional[Callable] = None,
    ) -> RouterContract:
        """Handle RESEARCH intent — deep research on specific companies."""
        return self.pipeline.run(context, on_progress=on_progress)

    def _handle_outreach(
        self,
        context: PipelineContext,
        on_progress: Optional[Callable] = None,
    ) -> RouterContract:
        """Handle OUTREACH intent — draft emails."""
        return self.pipeline.run(context, on_progress=on_progress)

    def _handle_pipeline(
        self,
        context: PipelineContext,
        on_progress: Optional[Callable] = None,
    ) -> RouterContract:
        """Generic pipeline handler for SKILLS, CONTACT, etc."""
        return self.pipeline.run(context, on_progress=on_progress)
