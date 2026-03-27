"""Tests for src/pylon/agents/skills.py — SkillsAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.skills import SkillsAgent
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyProfile,
    ContractStatus,
    FundingStage,
    PipelineContext,
)

MOCK_SKILLS_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "tools_used": ["Python", "PostgreSQL", "Docker"],
        "ml_frameworks": ["PyTorch", "scikit-learn"],
        "cloud_platform": "AWS",
        "skills_to_learn": ["Computer Vision", "Real-time data pipelines"],
        "alignment_score": 0.75,
        "gap_analysis": "Strong Python/ML foundation. Need to develop CV and streaming skills.",
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.skills.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_SKILLS_RESPONSE
        mock_cls.return_value = mock_client
        a = SkillsAgent()
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
        ),
    ]
    return ctx


class TestSkillsAgent:
    def test_run_populates_skills(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.skills) == 1
        assert context.skills[0].company_name == "StatsBomb"
        assert context.skills[0].alignment_score == 0.75

    def test_ml_frameworks_parsed(self, agent, context):
        agent.run(context)
        assert "PyTorch" in context.skills[0].ml_frameworks

    def test_no_profiles_returns_empty(self, agent, context):
        context.profiles = []
        contract = agent.run(context)
        assert len(context.skills) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_alignment_score_clamped(self, agent, context):
        response = json.dumps([{
            "company_name": "TestCo",
            "alignment_score": 5.0,
        }])
        agent.client.call.return_value = response
        agent.run(context)
        assert context.skills[0].alignment_score == 1.0

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "invalid"
        contract = agent.run(context)
        assert len(context.skills) == 0

    def test_run_with_web_search(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = True
        mock_search.search_context.return_value = (
            "[StatsBomb Jobs](https://statsbomb.com/jobs)\nLooking for PyTorch expertise"
        )
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real job posting" in user_msg
        assert "StatsBomb Jobs" in user_msg

    def test_run_without_web_search_fallback(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = False
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real job posting" not in user_msg
