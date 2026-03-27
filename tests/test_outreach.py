"""Tests for src/pylon/agents/outreach.py — OutreachAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.outreach import OutreachAgent
from pylon.models import (
    ContactInfo,
    CompanyProfile,
    ContractStatus,
    PipelineContext,
    ResumeVersion,
)

MOCK_OUTREACH_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "contact_name": "Ted Knutson",
        "subject": "ML Engineer Passionate About Football Analytics",
        "body": "Hi Ted, I've been following StatsBomb's open data initiatives...",
        "personalization_notes": "Referenced open data and xG model",
        "template_used": "cold",
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.outreach.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_OUTREACH_RESPONSE
        mock_cls.return_value = mock_client
        a = OutreachAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.contacts = [ContactInfo(company_name="StatsBomb", name="Ted Knutson", title="CEO")]
    ctx.profiles = [CompanyProfile(company_name="StatsBomb", ml_use_cases=["xG"])]
    ctx.resumes = [ResumeVersion(company_name="StatsBomb", tailored_summary="ML + football")]
    return ctx


class TestOutreachAgent:
    def test_run_populates_drafts(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.drafts) == 1
        assert context.drafts[0].subject == "ML Engineer Passionate About Football Analytics"

    def test_no_contacts_returns_empty(self, agent, context):
        context.contacts = []
        contract = agent.run(context)
        assert len(context.drafts) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_handles_malformed_json(self, agent, context):
        agent.client.call.return_value = "invalid"
        contract = agent.run(context)
        assert len(context.drafts) == 0
