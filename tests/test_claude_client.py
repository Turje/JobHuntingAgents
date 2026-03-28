"""Tests for src/pylon/core/claude_client.py — Claude API wrapper."""

from unittest.mock import MagicMock, patch

import anthropic
import pytest


FAKE_API_KEY = "sk-ant-test-key"
FAKE_RESPONSE_TEXT = "Here are 10 football analytics companies..."


def _make_mock_response(text: str = FAKE_RESPONSE_TEXT) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


def _make_client(agent_name: str = "test_agent"):
    """Instantiate ClaudeClient with patched API key."""
    with patch("pylon.config.ANTHROPIC_API_KEY", FAKE_API_KEY):
        from pylon.core.claude_client import ClaudeClient
        client = ClaudeClient.__new__(ClaudeClient)
        client.agent_name = agent_name
        client._client = MagicMock()
        import logging
        client._logger = logging.getLogger(f"claude_client.{agent_name}")
        return client


class TestClaudeClientInit:
    def test_raises_when_key_missing(self):
        with patch("pylon.core.claude_client.ANTHROPIC_API_KEY", ""):
            from pylon.core.claude_client import ClaudeClient
            with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                ClaudeClient(agent_name="test")

    def test_agent_name_stored(self):
        client = _make_client("discovery")
        assert client.agent_name == "discovery"


class TestClaudeClientCall:
    def test_returns_response_text(self):
        client = _make_client()
        mock_resp = _make_mock_response(FAKE_RESPONSE_TEXT)
        client._client.messages.create.return_value = mock_resp
        result = client.call(
            system_prompt="You are a job hunting assistant.",
            user_message="Find football companies",
        )
        assert result == FAKE_RESPONSE_TEXT

    def test_raises_on_empty_content(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.content = []
        client._client.messages.create.return_value = mock_resp
        with pytest.raises(ValueError, match="empty content"):
            client.call(system_prompt="test", user_message="test")

    def test_retries_on_rate_limit(self):
        client = _make_client()
        mock_resp = _make_mock_response()
        rate_err = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "rate limited", "type": "rate_limit_error"}},
        )
        client._client.messages.create.side_effect = [rate_err, mock_resp]
        with patch("pylon.core.claude_client.RETRY_BASE_DELAY", 0.01), \
             patch("pylon.core.claude_client.MAX_RETRIES", 3):
            result = client.call(system_prompt="test", user_message="test")
        assert result == FAKE_RESPONSE_TEXT
        assert client._client.messages.create.call_count == 2

    def test_fails_fast_on_auth_error(self):
        client = _make_client()
        auth_err = anthropic.AuthenticationError(
            message="invalid key",
            response=MagicMock(status_code=401, headers={}),
            body={"error": {"message": "invalid key", "type": "authentication_error"}},
        )
        client._client.messages.create.side_effect = auth_err
        with pytest.raises(anthropic.AuthenticationError):
            client.call(system_prompt="test", user_message="test")
        assert client._client.messages.create.call_count == 1

    def test_exhausts_retries(self):
        client = _make_client()
        rate_err = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "rate limited", "type": "rate_limit_error"}},
        )
        client._client.messages.create.side_effect = rate_err
        with patch("pylon.core.claude_client.RETRY_BASE_DELAY", 0.01), \
             patch("pylon.core.claude_client.MAX_RETRIES", 2):
            with pytest.raises(anthropic.RateLimitError):
                client.call(system_prompt="test", user_message="test")
        assert client._client.messages.create.call_count == 2
