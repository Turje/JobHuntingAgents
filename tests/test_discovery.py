"""Tests for src/pylon/agents/discovery.py — DiscoveryAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.discovery import DiscoveryAgent
from pylon.models import (
    ContractStatus,
    IndustryDomain,
    Intent,
    IntentPriority,
    PipelineContext,
)

MOCK_DISCOVERY_RESPONSE = json.dumps([
    {
        "name": "StatsBomb",
        "domain": "sports_tech",
        "relevance_reason": "Football analytics leader",
        "website": "https://statsbomb.com",
        "confidence": 0.95,
    },
    {
        "name": "Opta Sports",
        "domain": "sports_tech",
        "relevance_reason": "Premier League data provider",
        "website": "https://optasports.com",
        "confidence": 0.88,
    },
    {
        "name": "Second Spectrum",
        "domain": "sports_tech",
        "relevance_reason": "Tracking data and ML for sports",
        "website": "https://secondspectrum.com",
        "confidence": 0.82,
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.discovery.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_DISCOVERY_RESPONSE
        mock_cls.return_value = mock_client
        a = DiscoveryAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football analytics companies")
    ctx.intent = Intent(
        priority=IntentPriority.DISCOVER,
        domain=IndustryDomain.SPORTS_TECH,
        raw_query="find football analytics companies",
    )
    return ctx


class TestDiscoveryAgent:
    def test_run_populates_candidates(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.candidates) == 3
        assert context.candidates[0].name == "StatsBomb"
        assert context.candidates[0].confidence == 0.95

    def test_candidates_sorted_by_confidence(self, agent, context):
        contract = agent.run(context)
        confidences = [c.confidence for c in context.candidates]
        assert confidences == sorted(confidences, reverse=True)

    def test_domain_parsed_correctly(self, agent, context):
        agent.run(context)
        assert context.candidates[0].domain == IndustryDomain.SPORTS_TECH

    def test_handles_empty_response(self, agent, context):
        agent.client.call.return_value = "[]"
        contract = agent.run(context)
        assert contract.blocking is True
        assert len(context.candidates) == 0

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "not json at all"
        contract = agent.run(context)
        assert contract.blocking is True
        assert len(context.candidates) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API down")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED
        assert contract.blocking is True

    def test_handles_markdown_fenced_json(self, agent, context):
        fenced = f"```json\n{MOCK_DISCOVERY_RESPONSE}\n```"
        agent.client.call.return_value = fenced
        contract = agent.run(context)
        assert len(context.candidates) == 3

    def test_invalid_domain_defaults_to_general(self, agent, context):
        response = json.dumps([{
            "name": "XCorp",
            "domain": "unknown_domain",
            "relevance_reason": "test",
            "confidence": 0.5,
        }])
        agent.client.call.return_value = response
        agent.run(context)
        assert context.candidates[0].domain == IndustryDomain.GENERAL

    def test_confidence_clamped(self, agent, context):
        response = json.dumps([{
            "name": "OverCorp",
            "relevance_reason": "test",
            "confidence": 5.0,
        }])
        agent.client.call.return_value = response
        agent.run(context)
        assert context.candidates[0].confidence == 1.0
