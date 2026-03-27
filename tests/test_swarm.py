"""Tests for src/pylon/workflows/swarm.py — SwarmWorkflow."""

from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    IndustryDomain,
    SwarmChannel,
    SwarmResult,
)
from pylon.workflows.swarm import SwarmWorkflow


def _mock_worker(channel: SwarmChannel) -> SwarmResult:
    """Simple mock worker that returns a result for each channel."""
    return SwarmResult(
        channel_id=channel.channel_id,
        company_name=channel.company_name,
        findings=f"Researched {channel.company_name}: uses ML for analytics",
        confidence=0.8,
    )


def _failing_worker(channel: SwarmChannel) -> SwarmResult:
    """Worker that always fails."""
    raise RuntimeError(f"Research failed for {channel.company_name}")


class TestSwarmWorkflow:
    def test_empty_candidates(self):
        swarm = SwarmWorkflow()
        results, contract = swarm.run([], _mock_worker)
        assert len(results) == 0
        assert contract.status == ContractStatus.EXECUTED

    def test_single_candidate(self):
        candidates = [
            CompanyCandidate(name="StatsBomb", relevance_reason="Football analytics"),
        ]
        swarm = SwarmWorkflow()
        results, contract = swarm.run(candidates, _mock_worker)
        assert len(results) == 1
        assert results[0].company_name == "StatsBomb"
        assert results[0].confidence == 0.8

    def test_multiple_candidates(self):
        candidates = [
            CompanyCandidate(name="StatsBomb", relevance_reason="Football"),
            CompanyCandidate(name="Opta", relevance_reason="Data"),
            CompanyCandidate(name="SecondSpectrum", relevance_reason="Tracking"),
        ]
        swarm = SwarmWorkflow(max_workers=3)
        results, contract = swarm.run(candidates, _mock_worker)
        assert len(results) == 3
        assert contract.status == ContractStatus.SWARM_COMPLETE
        names = {r.company_name for r in results}
        assert names == {"StatsBomb", "Opta", "SecondSpectrum"}

    def test_worker_failure_produces_error_result(self):
        candidates = [
            CompanyCandidate(name="FailCo", relevance_reason="test"),
        ]
        swarm = SwarmWorkflow()
        results, contract = swarm.run(candidates, _failing_worker)
        assert len(results) == 1
        assert results[0].confidence == 0.0
        assert "failed" in results[0].findings.lower()
        assert contract.critical_issues == 1

    def test_mixed_success_and_failure(self):
        candidates = [
            CompanyCandidate(name="GoodCo", relevance_reason="good"),
            CompanyCandidate(name="BadCo", relevance_reason="bad"),
        ]

        call_count = 0

        def mixed_worker(channel: SwarmChannel) -> SwarmResult:
            nonlocal call_count
            call_count += 1
            if channel.company_name == "BadCo":
                raise RuntimeError("Network error")
            return SwarmResult(
                channel_id=channel.channel_id,
                company_name=channel.company_name,
                findings="Success",
                confidence=0.9,
            )

        swarm = SwarmWorkflow(max_workers=2)
        results, contract = swarm.run(candidates, mixed_worker)
        assert len(results) == 2
        assert contract.critical_issues == 1

    def test_contract_confidence_calculated(self):
        candidates = [
            CompanyCandidate(name="A", relevance_reason="test"),
            CompanyCandidate(name="B", relevance_reason="test"),
        ]
        swarm = SwarmWorkflow()
        results, contract = swarm.run(candidates, _mock_worker)
        # avg confidence is 0.8, * 100 = 80.0, capped at 95
        assert contract.confidence == 80.0
