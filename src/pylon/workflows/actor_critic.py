"""
Actor-Critic workflow engine for JobHuntingAgents.
Max 3 cycles: actor creates/refines → critic reviews → APPROVED or REQUEST_CHANGES.
Adapted from 21Agents actor_critic.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pylon.models import ContractStatus, RouterContract

_logger = logging.getLogger("workflow.actor_critic")

MAX_AC_CYCLES = 3


class ActorProtocol(ABC):
    """Interface for an actor in the AC loop."""

    @abstractmethod
    def act(self, task: str, feedback: str = "") -> tuple[str, RouterContract]:
        """Produce or refine output. Returns (output_text, contract)."""


class CriticProtocol(ABC):
    """Interface for a critic in the AC loop."""

    @abstractmethod
    def critique(self, actor_output: str, task: str) -> RouterContract:
        """Review the actor's output. Returns contract with APPROVED or REQUEST_CHANGES."""


class ActorCriticWorkflow:
    """
    Runs an Actor-Critic refinement loop.

    1. Actor produces output based on task
    2. Critic reviews output
    3. If APPROVED → return output
    4. If REQUEST_CHANGES → feed critique back to actor, repeat
    5. After MAX_AC_CYCLES → escalate
    """

    def __init__(self, actor: ActorProtocol, critic: CriticProtocol) -> None:
        self.actor = actor
        self.critic = critic

    def run(self, task: str) -> tuple[str, RouterContract, int]:
        """
        Execute the AC loop.

        Returns:
            (final_output, final_contract, cycles_used)
        """
        feedback = ""
        for cycle in range(1, MAX_AC_CYCLES + 1):
            _logger.info("AC cycle %d/%d starting", cycle, MAX_AC_CYCLES)

            # Actor phase
            output, actor_contract = self.actor.act(task, feedback=feedback)
            _logger.info(
                "Actor produced output (confidence=%.1f, status=%s)",
                actor_contract.confidence,
                actor_contract.status.value,
            )

            if actor_contract.blocking:
                _logger.warning("Actor reported blocking issue, escalating")
                return output, actor_contract, cycle

            # Critic phase
            critic_contract = self.critic.critique(output, task)
            _logger.info(
                "Critic verdict: %s (confidence=%.1f, issues=%d)",
                critic_contract.status.value,
                critic_contract.confidence,
                critic_contract.critical_issues,
            )

            if critic_contract.is_approvable():
                _logger.info("AC loop approved after %d cycle(s)", cycle)
                return output, critic_contract, cycle

            # Prepare feedback for next cycle
            feedback = critic_contract.kb_update_notes or critic_contract.evidence or "Improve quality"
            _logger.info("Critic requested changes: %s", feedback[:100])

        # Exhausted cycles
        _logger.warning("AC loop exhausted %d cycles, escalating", MAX_AC_CYCLES)
        escalate_contract = RouterContract(
            status=ContractStatus.ESCALATE,
            confidence=actor_contract.confidence,
            critical_issues=actor_contract.critical_issues + 1,
            blocking=False,
            kb_update_notes=f"AC loop exceeded {MAX_AC_CYCLES} cycles",
        )
        return output, escalate_contract, MAX_AC_CYCLES
