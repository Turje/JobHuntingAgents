"""Tests for src/pylon/engine/search.py — WebSearchEngine (Serper + Google CSE fallback)."""

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from pylon.engine.search import WebSearchEngine


def _mock_response(data: dict) -> MagicMock:
    """Create a mock HTTP response with JSON data."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


SERPER_RESULTS = {
    "organic": [
        {"title": "Acme Careers", "link": "https://acme.com/careers", "snippet": "Hiring ML engineers"},
        {"title": "Acme Blog", "link": "https://acme.com/blog", "snippet": "CV research"},
    ]
}

GOOGLE_CSE_RESULTS = {
    "items": [
        {"title": "Acme Google", "link": "https://acme.com/g", "snippet": "From Google CSE"},
    ]
}


class TestNoKeys:
    def test_not_available(self):
        engine = WebSearchEngine()
        assert engine.is_available is False

    def test_search_returns_empty(self):
        engine = WebSearchEngine()
        assert engine.search("test") == []

    def test_search_context_returns_empty(self):
        engine = WebSearchEngine()
        assert engine.search_context("test") == ""


class TestSerperOnly:
    def test_is_available(self):
        engine = WebSearchEngine(serper_api_key="sk")
        assert engine.is_available is True

    def test_search_returns_results(self):
        engine = WebSearchEngine(serper_api_key="sk")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response(SERPER_RESULTS)):
            results = engine.search("acme", max_results=5)
        assert len(results) == 2
        assert results[0]["title"] == "Acme Careers"
        assert results[0]["url"] == "https://acme.com/careers"
        assert results[0]["content"] == "Hiring ML engineers"

    def test_sends_correct_headers(self):
        engine = WebSearchEngine(serper_api_key="my-key")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response(SERPER_RESULTS)) as mock:
            engine.search("test", max_results=3)
        req = mock.call_args[0][0]
        assert req.get_header("X-api-key") == "my-key"
        payload = json.loads(req.data)
        assert payload["q"] == "test"
        assert payload["num"] == 3

    def test_caps_at_100(self):
        engine = WebSearchEngine(serper_api_key="sk")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response({"organic": []})) as mock:
            engine.search("test", max_results=200)
        payload = json.loads(mock.call_args[0][0].data)
        assert payload["num"] == 100

    def test_network_error_returns_empty(self):
        engine = WebSearchEngine(serper_api_key="sk")
        with patch("pylon.engine.search.urlopen", side_effect=ConnectionError("down")):
            assert engine.search("test") == []


class TestGoogleCSEOnly:
    def test_is_available(self):
        engine = WebSearchEngine(google_api_key="gk", google_cse_id="cx")
        assert engine.is_available is True

    def test_search_returns_results(self):
        engine = WebSearchEngine(google_api_key="gk", google_cse_id="cx")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response(GOOGLE_CSE_RESULTS)):
            results = engine.search("acme")
        assert len(results) == 1
        assert results[0]["title"] == "Acme Google"
        assert results[0]["url"] == "https://acme.com/g"

    def test_google_cse_caps_at_10(self):
        engine = WebSearchEngine(google_api_key="gk", google_cse_id="cx")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response({"items": []})) as mock:
            engine.search("test", max_results=50)
        url = mock.call_args[0][0].full_url
        assert "num=10" in url

    def test_missing_cse_id_not_available(self):
        engine = WebSearchEngine(google_api_key="gk")
        assert engine.is_available is False


class TestFallback:
    def test_serper_fails_falls_back_to_google(self):
        """When Serper returns HTTP 429 (rate limited), Google CSE is used."""
        engine = WebSearchEngine(serper_api_key="sk", google_api_key="gk", google_cse_id="cx")

        serper_error = HTTPError("url", 429, "Too Many Requests", {}, None)
        call_count = 0

        def side_effect(req, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise serper_error
            return _mock_response(GOOGLE_CSE_RESULTS)

        with patch("pylon.engine.search.urlopen", side_effect=side_effect):
            results = engine.search("test")

        assert len(results) == 1
        assert results[0]["title"] == "Acme Google"
        assert call_count == 2

    def test_serper_network_error_falls_back(self):
        """Network error on Serper triggers Google CSE fallback."""
        engine = WebSearchEngine(serper_api_key="sk", google_api_key="gk", google_cse_id="cx")

        call_count = 0

        def side_effect(req, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("timeout")
            return _mock_response(GOOGLE_CSE_RESULTS)

        with patch("pylon.engine.search.urlopen", side_effect=side_effect):
            results = engine.search("test")

        assert len(results) == 1
        assert results[0]["title"] == "Acme Google"

    def test_both_fail_returns_empty(self):
        """When both engines fail, returns empty list."""
        engine = WebSearchEngine(serper_api_key="sk", google_api_key="gk", google_cse_id="cx")

        with patch("pylon.engine.search.urlopen", side_effect=ConnectionError("all down")):
            assert engine.search("test") == []

    def test_serper_success_skips_google(self):
        """When Serper succeeds, Google CSE is never called."""
        engine = WebSearchEngine(serper_api_key="sk", google_api_key="gk", google_cse_id="cx")

        with patch("pylon.engine.search.urlopen", return_value=_mock_response(SERPER_RESULTS)) as mock:
            results = engine.search("test")

        assert len(results) == 2
        assert results[0]["title"] == "Acme Careers"
        mock.assert_called_once()  # only Serper called


class TestSearchContext:
    def test_concatenates_results(self):
        engine = WebSearchEngine(serper_api_key="sk")
        with patch("pylon.engine.search.urlopen", return_value=_mock_response(SERPER_RESULTS)):
            text = engine.search_context("test")
        assert "[Acme Careers](https://acme.com/careers)" in text
        assert "Hiring ML engineers" in text
        assert "[Acme Blog](https://acme.com/blog)" in text
        assert "---" in text

    def test_empty_when_no_results(self):
        engine = WebSearchEngine()
        assert engine.search_context("test") == ""
