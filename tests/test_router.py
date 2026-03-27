"""Tests for src/pylon/router.py — PylonRouter."""

from unittest.mock import MagicMock, patch

import pytest

from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    IntentPriority,
    PipelineContext,
    RouterContract,
)


@pytest.fixture
def router():
    with patch("pylon.agents.discovery.ClaudeClient"):
        from pylon.router import PylonRouter
        return PylonRouter()


class TestPylonRouter:
    def test_emergency_intent(self, router):
        ctx, contract = router.handle_intent("stop everything")
        assert ctx.intent.priority == IntentPriority.EMERGENCY
        assert contract.status == ContractStatus.EXECUTED

    def test_review_intent(self, router):
        ctx, contract = router.handle_intent("show me progress")
        assert ctx.intent.priority == IntentPriority.REVIEW
        assert contract.status == ContractStatus.EXECUTED

    def test_discover_dispatches_pipeline(self, router):
        mock_contract = RouterContract(
            status=ContractStatus.EXECUTED,
            confidence=80.0,
        )
        with patch.object(router.pipeline, "run", return_value=mock_contract) as mock_run:
            ctx, contract = router.handle_intent("find football companies")
            assert ctx.intent.priority == IntentPriority.DISCOVER
            mock_run.assert_called_once()
            assert contract.status == ContractStatus.EXECUTED

    def test_session_stored(self, router):
        mock_contract = RouterContract(status=ContractStatus.EXECUTED, confidence=80.0)
        with patch.object(router.pipeline, "run", return_value=mock_contract):
            ctx, _ = router.handle_intent("find companies")
            stored = router.get_session(ctx.run_id)
            assert stored is not None
            assert stored.query == "find companies"

    def test_progress_callback(self, router):
        progress_events = []

        def on_progress(step, data):
            progress_events.append((step, data))

        mock_contract = RouterContract(status=ContractStatus.EXECUTED, confidence=80.0)
        with patch.object(router.pipeline, "run", return_value=mock_contract):
            router.handle_intent("find companies", on_progress=on_progress)

    def test_knowledge_updated_on_contract(self, router):
        mock_contract = RouterContract(
            status=ContractStatus.EXECUTED,
            confidence=80.0,
            kb_update_notes="Found 10 companies",
        )
        with patch.object(router.pipeline, "run", return_value=mock_contract), \
             patch.object(router.knowledge, "update_from_contract") as mock_kb:
            router.handle_intent("find companies")
            mock_kb.assert_called_once_with("Found 10 companies", "")
