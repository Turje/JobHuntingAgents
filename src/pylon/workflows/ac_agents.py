"""
AC agents — SearchPlanner, SearchCritic, OutreachCritic.
Concrete implementations of ActorProtocol and CriticProtocol.
"""

from __future__ import annotations

import logging

from pylon.config import DSPY_ENABLED
from pylon.core.claude_client import ClaudeClient
from pylon.models import ContractStatus, RouterContract
from pylon.workflows.actor_critic import ActorProtocol, CriticProtocol


class SearchPlanner(ActorProtocol):
    """Plans a search strategy for company discovery."""

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="search_planner")
        self.logger = logging.getLogger("ac.search_planner")

    @property
    def _use_dspy(self) -> bool:
        return DSPY_ENABLED

    def act(self, task: str, feedback: str = "") -> tuple[str, RouterContract]:
        if self._use_dspy:
            return self._act_dspy(task, feedback)
        return self._act_claude(task, feedback)

    def _act_dspy(self, task: str, feedback: str) -> tuple[str, RouterContract]:
        """Plan search strategy via DSPy module."""
        try:
            from pylon.dspy_.modules import PlanSearchModule

            module = PlanSearchModule()
            prediction = module(task=task, feedback=feedback)
            plan = prediction.plan
            contract = RouterContract(
                status=ContractStatus.PLANNED,
                confidence=70.0,
                kb_update_notes="Search plan created (DSPy)",
            )
            return plan, contract
        except Exception as exc:
            self.logger.error("SearchPlanner DSPy failed: %s", exc)
            return "", RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Planning (DSPy) failed: {exc}",
            )

    def _act_claude(self, task: str, feedback: str) -> tuple[str, RouterContract]:
        """Plan search strategy via direct ClaudeClient call."""
        system_prompt = (
            "You are a search strategy planner for job hunting.\n"
            "Given a user's interests, create a search plan that identifies:\n"
            "1. Target industries and sub-sectors\n"
            "2. Company types (startup, enterprise, consultancy)\n"
            "3. Geographic focus\n"
            "4. Key search terms and filters\n"
            "5. Expected company count (10-15)\n\n"
            "Return a structured search plan as text."
        )
        user_msg = f"Task: {task}"
        if feedback:
            user_msg += f"\n\nPrevious feedback to address:\n{feedback}"

        try:
            output = self.client.call(system_prompt=system_prompt, user_message=user_msg)
            contract = RouterContract(
                status=ContractStatus.PLANNED,
                confidence=70.0,
                kb_update_notes="Search plan created",
            )
            return output, contract
        except Exception as exc:
            self.logger.error("SearchPlanner failed: %s", exc)
            return "", RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Planning failed: {exc}",
            )


class SearchCritic(CriticProtocol):
    """Reviews a search plan for completeness and quality."""

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="search_critic")
        self.logger = logging.getLogger("ac.search_critic")

    @property
    def _use_dspy(self) -> bool:
        return DSPY_ENABLED

    def critique(self, actor_output: str, task: str) -> RouterContract:
        if self._use_dspy:
            return self._critique_dspy(actor_output, task)
        return self._critique_claude(actor_output, task)

    def _critique_dspy(self, actor_output: str, task: str) -> RouterContract:
        """Critique search plan via DSPy module."""
        try:
            from pylon.dspy_.modules import CritiqueSearchModule

            module = CritiqueSearchModule()
            prediction = module(task=task, plan=actor_output)
            verdict = prediction.verdict.upper()

            if "APPROVED" in verdict:
                return RouterContract(
                    status=ContractStatus.APPROVED,
                    confidence=80.0,
                    kb_update_notes="Search plan approved (DSPy)",
                )
            else:
                return RouterContract(
                    status=ContractStatus.REQUEST_CHANGES,
                    confidence=40.0,
                    kb_update_notes=prediction.verdict[:500],
                    evidence="Critic requested changes (DSPy)",
                )
        except Exception as exc:
            self.logger.error("SearchCritic DSPy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.APPROVED,
                confidence=60.0,
                kb_update_notes=f"Critic (DSPy) unavailable, auto-approving: {exc}",
            )

    def _critique_claude(self, actor_output: str, task: str) -> RouterContract:
        """Critique search plan via direct ClaudeClient call."""
        system_prompt = (
            "You are a search strategy critic for job hunting.\n"
            "Review the search plan and check:\n"
            "1. Does it cover the user's interests?\n"
            "2. Are the target industries appropriate?\n"
            "3. Is the company count reasonable (10-15)?\n"
            "4. Are search terms specific enough?\n\n"
            "If the plan is good, respond with: APPROVED\n"
            "If changes needed, respond with: REQUEST_CHANGES followed by specific feedback.\n"
            "Also provide a confidence score (0-100) for plan quality."
        )
        user_msg = f"Original task: {task}\n\nSearch plan to review:\n{actor_output}"

        try:
            response = self.client.call(system_prompt=system_prompt, user_message=user_msg)
            response_upper = response.upper()

            if "APPROVED" in response_upper:
                return RouterContract(
                    status=ContractStatus.APPROVED,
                    confidence=80.0,
                    kb_update_notes="Search plan approved",
                )
            else:
                return RouterContract(
                    status=ContractStatus.REQUEST_CHANGES,
                    confidence=40.0,
                    kb_update_notes=response[:500],
                    evidence="Critic requested changes",
                )
        except Exception as exc:
            self.logger.error("SearchCritic failed: %s", exc)
            # On critic failure, approve with lower confidence to avoid blocking
            return RouterContract(
                status=ContractStatus.APPROVED,
                confidence=60.0,
                kb_update_notes=f"Critic unavailable, auto-approving: {exc}",
            )


class OutreachCritic(CriticProtocol):
    """Reviews outreach email drafts for quality and personalization."""

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="outreach_critic")
        self.logger = logging.getLogger("ac.outreach_critic")

    @property
    def _use_dspy(self) -> bool:
        return DSPY_ENABLED

    def critique(self, actor_output: str, task: str) -> RouterContract:
        if self._use_dspy:
            return self._critique_dspy(actor_output, task)
        return self._critique_claude(actor_output, task)

    def _critique_dspy(self, actor_output: str, task: str) -> RouterContract:
        """Critique outreach draft via DSPy module."""
        try:
            from pylon.dspy_.modules import CritiqueOutreachModule

            module = CritiqueOutreachModule()
            prediction = module(context=task, draft=actor_output)
            verdict = prediction.verdict.upper()

            if "APPROVED" in verdict:
                return RouterContract(
                    status=ContractStatus.APPROVED,
                    confidence=85.0,
                    kb_update_notes="Outreach draft approved (DSPy)",
                )
            else:
                return RouterContract(
                    status=ContractStatus.REQUEST_CHANGES,
                    confidence=35.0,
                    kb_update_notes=prediction.verdict[:500],
                    evidence="Outreach critic requested changes (DSPy)",
                )
        except Exception as exc:
            self.logger.error("OutreachCritic DSPy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.APPROVED,
                confidence=60.0,
                kb_update_notes=f"Critic (DSPy) unavailable, auto-approving: {exc}",
            )

    def _critique_claude(self, actor_output: str, task: str) -> RouterContract:
        """Critique outreach draft via direct ClaudeClient call."""
        system_prompt = (
            "You are an outreach email critic.\n"
            "Review the cold email draft and check:\n"
            "1. Is it personalized to the recipient/company?\n"
            "2. Is the subject line compelling and under 80 chars?\n"
            "3. Is the body concise (under 300 words)?\n"
            "4. Does it avoid forbidden words (urgent, act now, guaranteed)?\n"
            "5. Does it have a clear call-to-action?\n\n"
            "If the email is good, respond with: APPROVED\n"
            "If changes needed, respond with: REQUEST_CHANGES followed by specific feedback."
        )
        user_msg = f"Context: {task}\n\nEmail draft to review:\n{actor_output}"

        try:
            response = self.client.call(system_prompt=system_prompt, user_message=user_msg)
            response_upper = response.upper()

            if "APPROVED" in response_upper:
                return RouterContract(
                    status=ContractStatus.APPROVED,
                    confidence=85.0,
                    kb_update_notes="Outreach draft approved",
                )
            else:
                return RouterContract(
                    status=ContractStatus.REQUEST_CHANGES,
                    confidence=35.0,
                    kb_update_notes=response[:500],
                    evidence="Outreach critic requested changes",
                )
        except Exception as exc:
            self.logger.error("OutreachCritic failed: %s", exc)
            return RouterContract(
                status=ContractStatus.APPROVED,
                confidence=60.0,
                kb_update_notes=f"Critic unavailable, auto-approving: {exc}",
            )
