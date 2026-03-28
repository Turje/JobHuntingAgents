"""Tests for src/pylon/core/claude_client.py — LLM client wrapper (Gemini + Anthropic)."""

import json
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from pylon.core.claude_client import ClaudeClient


FAKE_RESPONSE_TEXT = "Here are 10 football analytics companies..."


# ---- Helpers ----

def _make_gemini_client(agent_name: str = "test_agent"):
    """Create a Gemini-backed client without hitting real APIs."""
    with patch("pylon.core.claude_client.LLM_PROVIDER", "gemini"), \
         patch("pylon.core.claude_client.GEMINI_API_KEY", "fake-gemini-key"):
        client = ClaudeClient(agent_name)
    return client


def _make_anthropic_client(agent_name: str = "test_agent"):
    """Create an Anthropic-backed client without hitting real APIs."""
    with patch("pylon.core.claude_client.LLM_PROVIDER", "anthropic"), \
         patch("pylon.core.claude_client.ANTHROPIC_API_KEY", "fake-claude-key"):
        client = ClaudeClient(agent_name)
    client._anthropic_client = MagicMock()
    return client


def _mock_gemini_response(text: str = FAKE_RESPONSE_TEXT) -> MagicMock:
    """Mock urllib response for Gemini API."""
    data = {
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _mock_anthropic_response(text: str = FAKE_RESPONSE_TEXT) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


# ---- Init tests ----

class TestClientInit:
    def test_gemini_raises_when_key_missing(self):
        with patch("pylon.core.claude_client.LLM_PROVIDER", "gemini"), \
             patch("pylon.core.claude_client.GEMINI_API_KEY", ""):
            with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
                ClaudeClient(agent_name="test")

    def test_anthropic_raises_when_key_missing(self):
        with patch("pylon.core.claude_client.LLM_PROVIDER", "anthropic"), \
             patch("pylon.core.claude_client.ANTHROPIC_API_KEY", ""):
            with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                ClaudeClient(agent_name="test")

    def test_unknown_provider_raises(self):
        with patch("pylon.core.claude_client.LLM_PROVIDER", "openai"), \
             patch("pylon.core.claude_client.GEMINI_API_KEY", "key"):
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                ClaudeClient(agent_name="test")

    def test_agent_name_stored(self):
        client = _make_gemini_client("discovery")
        assert client.agent_name == "discovery"


# ---- Gemini tests ----

class TestGeminiCall:
    def test_returns_response_text(self):
        client = _make_gemini_client()
        with patch("pylon.core.claude_client.urlopen", return_value=_mock_gemini_response()):
            result = client.call(system_prompt="test", user_message="Find companies")
        assert result == FAKE_RESPONSE_TEXT

    def test_raises_on_empty_candidates(self):
        client = _make_gemini_client()
        resp = MagicMock()
        resp.read.return_value = json.dumps({"candidates": []}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("pylon.core.claude_client.urlopen", return_value=resp):
            with pytest.raises(ValueError, match="no candidates"):
                client.call(system_prompt="test", user_message="test")

    def test_retries_on_server_error(self):
        client = _make_gemini_client()
        from urllib.error import HTTPError
        err = HTTPError("url", 500, "Server Error", {}, None)
        with patch("pylon.core.claude_client.urlopen",
                    side_effect=[err, _mock_gemini_response()]), \
             patch("pylon.core.claude_client.RETRY_BASE_DELAY", 0.01), \
             patch("pylon.core.claude_client.MAX_RETRIES", 3):
            result = client.call(system_prompt="test", user_message="test")
        assert result == FAKE_RESPONSE_TEXT

    def test_fails_fast_on_auth_error(self):
        client = _make_gemini_client()
        from urllib.error import HTTPError
        err = HTTPError("url", 403, "Forbidden", {}, None)
        with patch("pylon.core.claude_client.urlopen", side_effect=err):
            with pytest.raises(HTTPError):
                client.call(system_prompt="test", user_message="test")


# ---- Anthropic tests ----

class TestAnthropicCall:
    def test_returns_response_text(self):
        client = _make_anthropic_client()
        client._anthropic_client.messages.create.return_value = _mock_anthropic_response()
        result = client.call(system_prompt="test", user_message="Find companies")
        assert result == FAKE_RESPONSE_TEXT

    def test_raises_on_empty_content(self):
        client = _make_anthropic_client()
        mock_resp = MagicMock()
        mock_resp.content = []
        client._anthropic_client.messages.create.return_value = mock_resp
        with pytest.raises(ValueError, match="empty content"):
            client.call(system_prompt="test", user_message="test")

    def test_retries_on_rate_limit(self):
        client = _make_anthropic_client()
        rate_err = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "rate limited", "type": "rate_limit_error"}},
        )
        client._anthropic_client.messages.create.side_effect = [
            rate_err, _mock_anthropic_response()
        ]
        with patch("pylon.core.claude_client.RETRY_BASE_DELAY", 0.01), \
             patch("pylon.core.claude_client.MAX_RETRIES", 3):
            result = client.call(system_prompt="test", user_message="test")
        assert result == FAKE_RESPONSE_TEXT

    def test_fails_fast_on_auth_error(self):
        client = _make_anthropic_client()
        auth_err = anthropic.AuthenticationError(
            message="invalid key",
            response=MagicMock(status_code=401, headers={}),
            body={"error": {"message": "invalid key", "type": "authentication_error"}},
        )
        client._anthropic_client.messages.create.side_effect = auth_err
        with pytest.raises(anthropic.AuthenticationError):
            client.call(system_prompt="test", user_message="test")
