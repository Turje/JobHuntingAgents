"""Tests for DSPy fallback behavior — DSPY_ENABLED toggle and error handling."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.models import (
    CompanyCandidate,
    CompanyProfile,
    ContactInfo,
    ContractStatus,
    Intent,
    IntentPriority,
    IndustryDomain,
    PipelineContext,
)


MOCK_DISCOVERY_RESPONSE = json.dumps([
    {"name": "Acme", "domain": "fintech", "relevance_reason": "Fintech leader",
     "website": "https://acme.com", "confidence": 0.9},
])


@pytest.fixture
def context():
    ctx = PipelineContext.new("find fintech companies")
    ctx.intent = Intent(priority=IntentPriority.DISCOVER, raw_query="find fintech companies")
    return ctx


class TestDspyDisabledFallback:
    """When DSPY_ENABLED=False, agents should use ClaudeClient path."""

    @patch("pylon.agents.base.DSPY_ENABLED", False)
    @patch("pylon.agents.discovery.ClaudeClient")
    def test_discovery_uses_claude_when_disabled(self, mock_cls, context):
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_DISCOVERY_RESPONSE
        mock_cls.return_value = mock_client

        from pylon.agents.discovery import DiscoveryAgent
        agent = DiscoveryAgent()
        agent.client = mock_client

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.candidates) == 1
        # ClaudeClient.call should have been invoked
        mock_client.call.assert_called_once()

    @patch("pylon.agents.base.DSPY_ENABLED", False)
    @patch("pylon.agents.research.ClaudeClient")
    def test_research_uses_claude_when_disabled(self, mock_cls, context):
        mock_client = MagicMock()
        mock_client.call.return_value = json.dumps([
            {"company_name": "Acme", "r_and_d_approach": "ML-first"}
        ])
        mock_cls.return_value = mock_client

        context.candidates = [
            CompanyCandidate(name="Acme", relevance_reason="Fintech", confidence=0.9)
        ]

        from pylon.agents.research import ResearchAgent
        agent = ResearchAgent()
        agent.client = mock_client

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        mock_client.call.assert_called_once()


class TestDspyEnabledErrorFallback:
    """When DSPY_ENABLED=True but DSPy module fails, return BLOCKED contract."""

    @patch("pylon.agents.base.DSPY_ENABLED", True)
    @patch("pylon.agents.discovery.ClaudeClient")
    def test_discovery_dspy_error_returns_blocked(self, mock_cls, context):
        mock_cls.return_value = MagicMock()

        from pylon.agents.discovery import DiscoveryAgent
        agent = DiscoveryAgent()

        # Patch the DSPy module import to raise
        with patch("pylon.agents.discovery.DiscoveryModule", side_effect=RuntimeError("DSPy not configured"), create=True):
            # The _run_dspy method does a local import, so we patch where it imports from
            with patch.dict("sys.modules", {"pylon.dspy_.modules": MagicMock()}):
                import sys
                mock_mod = sys.modules["pylon.dspy_.modules"]
                mock_mod.DiscoveryModule.side_effect = RuntimeError("DSPy not configured")
                contract = agent.run(context)
                assert contract.status == ContractStatus.BLOCKED
                assert contract.blocking is True
                assert "DSPy" in contract.kb_update_notes

    @patch("pylon.agents.base.DSPY_ENABLED", True)
    @patch("pylon.agents.outreach.ClaudeClient")
    def test_outreach_dspy_error_returns_blocked(self, mock_cls, context):
        mock_cls.return_value = MagicMock()

        context.contacts = [
            ContactInfo(company_name="Acme", name="John", title="CTO", confidence=0.9)
        ]

        from pylon.agents.outreach import OutreachAgent
        agent = OutreachAgent()

        with patch.dict("sys.modules", {"pylon.dspy_.modules": MagicMock()}):
            import sys
            mock_mod = sys.modules["pylon.dspy_.modules"]
            mock_mod.OutreachModule.side_effect = RuntimeError("DSPy not configured")
            contract = agent.run(context)
            assert contract.status == ContractStatus.BLOCKED
            assert contract.blocking is True
