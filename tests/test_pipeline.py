"""Tests for src/pylon/pipeline.py — FullSearchPipeline."""

from unittest.mock import MagicMock, patch

import pytest

from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    Intent,
    IntentPriority,
    PipelineContext,
    RouterContract,
)


@pytest.fixture
def pipeline():
    with patch("pylon.agents.discovery.ClaudeClient"):
        from pylon.pipeline import FullSearchPipeline
        return FullSearchPipeline()


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.intent = Intent(priority=IntentPriority.DISCOVER, raw_query="find football companies")
    return ctx


def _populate_candidates(ctx: PipelineContext, contract: RouterContract) -> RouterContract:
    ctx.candidates = [
        CompanyCandidate(name="StatsBomb", relevance_reason="Football analytics", confidence=0.9),
        CompanyCandidate(name="Opta", relevance_reason="Premier League data", confidence=0.8),
    ]
    return contract


class TestFullSearchPipeline:
    def test_discovery_only(self, pipeline, context):
        mock_contract = RouterContract(status=ContractStatus.EXECUTED, confidence=80.0)
        with patch.object(pipeline.discovery, "run") as mock_run:
            mock_run.side_effect = lambda ctx: _populate_candidates(ctx, mock_contract)
            contract = pipeline.run(context)
            assert contract.status == ContractStatus.EXECUTED
            mock_run.assert_called_once()

    def test_blocked_discovery_stops_pipeline(self, pipeline, context):
        blocked = RouterContract(status=ContractStatus.BLOCKED, confidence=0.0, blocking=True)
        with patch.object(pipeline.discovery, "run", return_value=blocked):
            contract = pipeline.run(context)
            assert contract.blocking is True

    def test_empty_discovery_stops_pipeline(self, pipeline, context):
        empty_contract = RouterContract(
            status=ContractStatus.EXECUTED, confidence=0.0, blocking=True
        )
        with patch.object(pipeline.discovery, "run", return_value=empty_contract):
            contract = pipeline.run(context)
            assert contract.blocking is True

    def test_progress_callbacks(self, pipeline, context):
        events = []

        def on_progress(step, data):
            events.append(step)

        mock_contract = RouterContract(status=ContractStatus.EXECUTED, confidence=80.0)
        with patch.object(pipeline.discovery, "run") as mock_run:
            mock_run.side_effect = lambda ctx: _populate_candidates(ctx, mock_contract)
            pipeline.run(context, on_progress=on_progress)
            assert "discovery_start" in events
            assert "discovery_complete" in events
            assert "pipeline_complete" in events
