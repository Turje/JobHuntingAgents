"""Tests for src/pylon/agents/contact.py — ContactAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pylon.agents.contact import ContactAgent
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyCandidate,
    CompanyProfile,
    ContractStatus,
    PipelineContext,
)

MOCK_CONTACT_RESPONSE = json.dumps([
    {
        "company_name": "StatsBomb",
        "name": "Ted Knutson",
        "title": "CEO & Founder",
        "email": "",
        "linkedin_url": "https://linkedin.com/in/tedknutson",
        "notes": "Founded StatsBomb, strong analytics background",
        "confidence": 0.8,
    },
])


@pytest.fixture
def agent():
    with patch("pylon.agents.contact.ClaudeClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_CONTACT_RESPONSE
        mock_cls.return_value = mock_client
        a = ContactAgent()
        a.client = mock_client
        return a


@pytest.fixture
def context():
    ctx = PipelineContext.new("find football companies")
    ctx.candidates = [
        CompanyCandidate(name="StatsBomb", relevance_reason="Football analytics"),
    ]
    ctx.profiles = [
        CompanyProfile(company_name="StatsBomb"),
    ]
    return ctx


class TestContactAgent:
    def test_run_populates_contacts(self, agent, context):
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        assert len(context.contacts) == 1
        assert context.contacts[0].name == "Ted Knutson"

    def test_no_companies_returns_empty(self, agent, context):
        context.candidates = []
        context.profiles = []
        contract = agent.run(context)
        assert len(context.contacts) == 0

    def test_handles_api_error(self, agent, context):
        agent.client.call.side_effect = Exception("API error")
        contract = agent.run(context)
        assert contract.status == ContractStatus.BLOCKED

    def test_uses_profiles_when_available(self, agent, context):
        agent.run(context)
        call_args = agent.client.call.call_args
        assert "StatsBomb" in call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))

    def test_falls_back_to_candidates(self, agent, context):
        context.profiles = []
        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED

    def test_run_with_web_search(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = True
        mock_search.search_context.return_value = (
            "[LinkedIn](https://linkedin.com)\nTed Knutson, CEO at StatsBomb"
        )
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real web data" in user_msg
        assert "Ted Knutson" in user_msg

    def test_run_without_web_search_fallback(self, agent, context):
        mock_search = MagicMock(spec=WebSearchEngine)
        mock_search.is_available = False
        agent.search = mock_search

        contract = agent.run(context)
        assert contract.status == ContractStatus.EXECUTED
        call_args = agent.client.call.call_args
        user_msg = call_args.kwargs.get("user_message", call_args[1].get("user_message", ""))
        assert "real web data" not in user_msg
