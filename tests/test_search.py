"""Tests for src/pylon/engine/search.py — WebSearchEngine."""

from unittest.mock import MagicMock, patch

import pytest

from pylon.engine.search import WebSearchEngine


class TestWebSearchEngine:
    def test_search_without_api_key(self):
        engine = WebSearchEngine(api_key="")
        assert engine.is_available is False
        assert engine.search("test query") == []

    def test_search_context_without_api_key(self):
        engine = WebSearchEngine(api_key="")
        assert engine.search_context("test query") == ""

    @patch("pylon.engine.search.TavilyClient", create=True)
    def test_search_with_mock_tavily(self, mock_tavily_cls):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Acme Corp Careers",
                    "url": "https://acme.com/careers",
                    "content": "We are hiring ML engineers",
                },
                {
                    "title": "Acme Blog",
                    "url": "https://acme.com/blog",
                    "content": "Our latest CV research",
                },
            ]
        }
        mock_tavily_cls.return_value = mock_client

        # Patch the import inside __init__
        with patch.dict("sys.modules", {"tavily": MagicMock(TavilyClient=mock_tavily_cls)}):
            engine = WebSearchEngine(api_key="tvly-test-key")
            engine._client = mock_client  # Ensure mock is used

        assert engine.is_available is True
        results = engine.search("acme corp", max_results=5)
        assert len(results) == 2
        assert results[0]["title"] == "Acme Corp Careers"
        assert results[0]["url"] == "https://acme.com/careers"
        assert results[0]["content"] == "We are hiring ML engineers"
        mock_client.search.assert_called_once_with(query="acme corp", max_results=5)

    @patch("pylon.engine.search.TavilyClient", create=True)
    def test_search_context_concatenates(self, mock_tavily_cls):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Page 1", "url": "https://a.com", "content": "Content A"},
                {"title": "Page 2", "url": "https://b.com", "content": "Content B"},
            ]
        }
        mock_tavily_cls.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": MagicMock(TavilyClient=mock_tavily_cls)}):
            engine = WebSearchEngine(api_key="tvly-test-key")
            engine._client = mock_client

        text = engine.search_context("test", max_results=5)
        assert "[Page 1](https://a.com)" in text
        assert "Content A" in text
        assert "[Page 2](https://b.com)" in text
        assert "Content B" in text
        assert "---" in text  # separator

    @patch("pylon.engine.search.TavilyClient", create=True)
    def test_search_handles_network_error(self, mock_tavily_cls):
        mock_client = MagicMock()
        mock_client.search.side_effect = ConnectionError("Network down")
        mock_tavily_cls.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": MagicMock(TavilyClient=mock_tavily_cls)}):
            engine = WebSearchEngine(api_key="tvly-test-key")
            engine._client = mock_client

        results = engine.search("test query")
        assert results == []

    @patch("pylon.engine.search.TavilyClient", create=True)
    def test_search_respects_max_results(self, mock_tavily_cls):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_tavily_cls.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": MagicMock(TavilyClient=mock_tavily_cls)}):
            engine = WebSearchEngine(api_key="tvly-test-key")
            engine._client = mock_client

        engine.search("test", max_results=3)
        mock_client.search.assert_called_once_with(query="test", max_results=3)
