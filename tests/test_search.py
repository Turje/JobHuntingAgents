"""Tests for src/pylon/engine/search.py — WebSearchEngine (Google Custom Search)."""

from unittest.mock import MagicMock, patch

import pytest

from pylon.engine.search import WebSearchEngine


class TestWebSearchEngine:
    def test_search_without_api_key(self):
        engine = WebSearchEngine(api_key="", cse_id="")
        assert engine.is_available is False
        assert engine.search("test query") == []

    def test_search_context_without_api_key(self):
        engine = WebSearchEngine(api_key="", cse_id="")
        assert engine.search_context("test query") == ""

    def test_search_with_mock_google(self):
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "items": [
                {
                    "title": "Acme Corp Careers",
                    "link": "https://acme.com/careers",
                    "snippet": "We are hiring ML engineers",
                },
                {
                    "title": "Acme Blog",
                    "link": "https://acme.com/blog",
                    "snippet": "Our latest CV research",
                },
            ]
        }
        mock_cse.list.return_value = mock_list
        mock_service.cse.return_value = mock_cse

        engine = WebSearchEngine(api_key="", cse_id="")
        engine._service = mock_service
        engine.cse_id = "test-cse-id"

        assert engine.is_available is True
        results = engine.search("acme corp", max_results=5)
        assert len(results) == 2
        assert results[0]["title"] == "Acme Corp Careers"
        assert results[0]["url"] == "https://acme.com/careers"
        assert results[0]["content"] == "We are hiring ML engineers"

    def test_search_context_concatenates(self):
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "items": [
                {"title": "Page 1", "link": "https://a.com", "snippet": "Content A"},
                {"title": "Page 2", "link": "https://b.com", "snippet": "Content B"},
            ]
        }
        mock_cse.list.return_value = mock_list
        mock_service.cse.return_value = mock_cse

        engine = WebSearchEngine(api_key="", cse_id="")
        engine._service = mock_service
        engine.cse_id = "test-cse-id"

        text = engine.search_context("test", max_results=5)
        assert "[Page 1](https://a.com)" in text
        assert "Content A" in text
        assert "[Page 2](https://b.com)" in text
        assert "Content B" in text
        assert "---" in text  # separator

    def test_search_handles_network_error(self):
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.side_effect = ConnectionError("Network down")
        mock_cse.list.return_value = mock_list
        mock_service.cse.return_value = mock_cse

        engine = WebSearchEngine(api_key="", cse_id="")
        engine._service = mock_service
        engine.cse_id = "test-cse-id"

        results = engine.search("test query")
        assert results == []

    def test_search_respects_max_results(self):
        mock_service = MagicMock()
        mock_cse = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {"items": []}
        mock_cse.list.return_value = mock_list
        mock_service.cse.return_value = mock_cse

        engine = WebSearchEngine(api_key="", cse_id="")
        engine._service = mock_service
        engine.cse_id = "test-cse-id"

        engine.search("test", max_results=3)
        mock_cse.list.assert_called_once_with(
            q="test", cx="test-cse-id", num=3, start=1
        )
