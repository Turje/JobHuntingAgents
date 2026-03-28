"""Tests for src/pylon/agents/tools.py — ToolSuggestionsAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.tools import ToolSuggestionsAgent
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyProfile,
    ContractStatus,
    PipelineContext,
    SkillsAnalysis,
)

MOCK_TOOLS_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "tool_name": "xG Predictor API",
        "description": "Real-time expected goals prediction API using event stream data.",
        "why_impressive": "Directly addresses their core product offering.",
        "estimated_revenue_impact": "$100K-500K/year in API licensing",
    },
    {
        "company_name": "StatsBomb",
        "tool_name": "Player Similarity Dashboard",
        "description": "Interactive dashboard comparing players using embedding similarity.",
        "why_impressive": "Showcases ML and visualization skills they need.",
        "estimated_revenue_impact": "$50K-200K/year savings in scouting",
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.tools.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_TOOLS_RESPONSE
        mock_cls.return_value = mock_client
        a = ToolSuggestionsAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.profiles = [
        CompanyProfile(
            company_name="StatsBomb",
            ml_use_cases=["expected goals", "player tracking"],
            r_and_d_approach="Data-driven",
            culture="Analytics-first",
            hiring_signals=["3 ML roles posted"],
        ),
    ]
    ctx.skills = [
        SkillsAnalysis(
            company_name="StatsBomb",
            tools_used=["Python", "PostgreSQL"],
            ml_frameworks=["PyTorch"],
            cloud_platform="AWS",
            alignment_score=0.75,
        ),
    ]
    return ctx


class TestToolSuggestionsAgent:
    def test_run_populates_tools(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.tools) == 2
        assert context.tools[0].company_name == "StatsBomb"
        assert context.tools[0].tool_name == "xG Predictor API"

    def test_no_profiles_returns_empty(self, agent, context):
        context.profiles = []
        contract = agent.run(context)
        assert len(context.tools) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "not json at all"
        contract = agent.run(context)
        assert len(context.tools) == 0

    def test_revenue_impact_parsed(self, agent, context):
        agent.run(context)
        assert "$100K-500K" in context.tools[0].estimated_revenue_impact

    def test_why_impressive_parsed(self, agent, context):
        agent.run(context)
        assert "core product" in context.tools[0].why_impressive
