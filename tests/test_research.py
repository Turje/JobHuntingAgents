"""Tests for src/pylon/agents/research.py — ResearchAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.research import ResearchAgent
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    FundingStage,
    IndustryDomain,
    PipelineContext,
)

MOCK_RESEARCH_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "r_and_d_approach": "Data-driven football analytics",
        "engineering_blog": "https://statsbomb.com/articles",
        "notable_clients": ["FC Barcelona", "Arsenal"],
        "culture": "Open data community, conference talks",
        "ml_use_cases": ["expected goals", "player tracking"],
        "funding_stage": "series_b",
        "hiring_signals": ["Posted ML Engineer role", "Growing team"],
        "headquarters": "Bath, UK",
        "employee_count": "50-100",
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.research.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_RESEARCH_RESPONSE
        mock_cls.return_value = mock_client
        a = ResearchAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.candidates = [
        CompanyCandidate(name="StatsBomb", relevance_reason="Football analytics", confidence=0.9),
    ]
    return ctx


class TestResearchAgent:
    def test_run_populates_profiles(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.profiles) == 1
        assert context.profiles[0].company_name == "StatsBomb"
        assert context.profiles[0].funding_stage == FundingStage.SERIES_B

    def test_notable_clients_parsed(self, agent, context):
        agent.run(context)
        assert "FC Barcelona" in context.profiles[0].notable_clients

    def test_no_candidates_returns_empty(self, agent, context):
        context.candidates = []
        contract = agent.run(context)
        assert len(context.profiles) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_handles_invalid_funding_stage(self, agent, context):
        response = json.dumps([{
            "company_name": "TestCo",
            "funding_stage": "mega_round",
        }])
        agent.client.call.return_value = response
        agent.run(context)
        assert context.profiles[0].funding_stage == FundingStage.UNKNOWN

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "not json"
        contract = agent.run(context)
        assert len(context.profiles) == 0

    def test_run_with_web_search(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = True
        mock_search.search_context.return_value = (
            "[StatsBomb Blog](https://statsbomb.com/blog)\nUsing xG models"
        )
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real web search data" in user_msg
        assert "StatsBomb Blog" in user_msg

    def test_run_without_web_search_fallback(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = False
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real web search data" not in user_msg
