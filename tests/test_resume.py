"""Tests for src/pylon/agents/resume.py — ResumeAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.resume import ResumeAgent
from pylon.models import (
    CompanyCandidate,
    CompanyProfile,
    ContractStatus,
    PipelineContext,
    SkillsAnalysis,
)

MOCK_RESUME_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "tailored_summary": "ML engineer with football analytics focus",
        "emphasis_areas": ["Computer Vision", "Sports Analytics"],
        "highlighted_projects": ["Player tracking system"],
        "tailored_bullets": ["Built CV pipeline processing 50K frames/day"],
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.resume.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_RESUME_RESPONSE
        mock_cls.return_value = mock_client
        a = ResumeAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.candidates = [CompanyCandidate(name="StatsBomb", relevance_reason="Football")]
    ctx.profiles = [CompanyProfile(company_name="StatsBomb", ml_use_cases=["xG"])]
    ctx.skills = [SkillsAnalysis(company_name="StatsBomb", alignment_score=0.8)]
    return ctx


class TestResumeAgent:
    def test_run_populates_resumes(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.resumes) == 1
        assert context.resumes[0].company_name == "StatsBomb"

    def test_no_candidates_returns_empty(self, agent, context):
        context.candidates = []
        contract = agent.run(context)
        assert len(context.resumes) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "not json"
        contract = agent.run(context)
        assert len(context.resumes) == 0
