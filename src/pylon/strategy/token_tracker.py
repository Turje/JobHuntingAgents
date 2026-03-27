"""
Token usage tracking across Pylon agents.
Gives visibility into per-agent and total token spend per pipeline run.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    """Aggregated token counts for a single agent."""

    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0

    @property
    def total(self) -> int:
        """Combined input + output tokens."""
        return self.input_tokens + self.output_tokens


class TokenTracker:
    """Records and reports per-agent token consumption."""

    def __init__(self) -> None:
        self._agents: dict[str, TokenUsage] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, agent_name: str, input_tokens: int, output_tokens: int) -> None:
        """Add a single LLM call's token counts for *agent_name*."""
        usage = self._agents.setdefault(agent_name, TokenUsage())
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.call_count += 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_total(self) -> TokenUsage:
        """Return aggregate usage across all agents."""
        total = TokenUsage()
        for usage in self._agents.values():
            total.input_tokens += usage.input_tokens
            total.output_tokens += usage.output_tokens
            total.call_count += usage.call_count
        return total

    def get_by_agent(self) -> dict[str, TokenUsage]:
        """Return a copy of per-agent usage mapping."""
        return dict(self._agents)

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded usage."""
        self._agents.clear()
