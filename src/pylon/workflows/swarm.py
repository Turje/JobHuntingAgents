"""
Swarm workflow — parallel multi-company research.
Decomposes a list of companies into parallel channels, runs research concurrently,
then aggregates results.
Adapted from 21Agents swarm.py.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable

from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    RouterContract,
    SwarmChannel,
    SwarmResult,
)

_logger = logging.getLogger("workflow.swarm")

MAX_SWARM_WORKERS = 5


class SwarmWorkflow:
    """
    Parallel research across multiple companies.
    Each company gets its own SwarmChannel processed by a worker function.
    """

    def __init__(self, max_workers: int = MAX_SWARM_WORKERS) -> None:
        self.max_workers = max_workers

    def run(
        self,
        candidates: list[CompanyCandidate],
        worker_fn: Callable[[SwarmChannel], SwarmResult],
    ) -> tuple[list[SwarmResult], RouterContract]:
        """
        Execute parallel research across all candidates.

        Args:
            candidates: Companies to research
            worker_fn: Function that takes a SwarmChannel and returns a SwarmResult

        Returns:
            (results, contract)
        """
        if not candidates:
            return [], RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No candidates to swarm",
            )

        channels = [
            SwarmChannel(
                company_name=c.name,
                task_description=f"Research {c.name}: {c.relevance_reason}",
                agent_type="research",
            )
            for c in candidates
        ]

        _logger.info("Swarm starting with %d channels, %d workers", len(channels), self.max_workers)

        results: list[SwarmResult] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_channel: dict[Future, SwarmChannel] = {
                executor.submit(worker_fn, ch): ch for ch in channels
            }

            for future, channel in future_to_channel.items():
                try:
                    result = future.result()
                    results.append(result)
                    _logger.info(
                        "Swarm channel %s completed (confidence=%.2f)",
                        channel.company_name,
                        result.confidence,
                    )
                except Exception as exc:
                    _logger.error(
                        "Swarm channel %s failed: %s", channel.company_name, exc
                    )
                    errors.append(f"{channel.company_name}: {exc}")
                    results.append(SwarmResult(
                        channel_id=channel.channel_id,
                        company_name=channel.company_name,
                        findings=f"Research failed: {exc}",
                        confidence=0.0,
                    ))

        avg_confidence = (
            sum(r.confidence for r in results) / len(results) if results else 0.0
        )

        contract = RouterContract(
            status=ContractStatus.SWARM_COMPLETE,
            confidence=min(95.0, avg_confidence * 100),
            critical_issues=len(errors),
            blocking=False,
            kb_update_notes=f"Swarm completed: {len(results)} channels, {len(errors)} errors",
        )

        _logger.info(
            "Swarm complete: %d results, %d errors, avg_confidence=%.2f",
            len(results),
            len(errors),
            avg_confidence,
        )

        return results, contract
