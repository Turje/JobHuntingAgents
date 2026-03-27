"""
Web search integration for JobHuntingAgents.
Uses Tavily API for real web search, with graceful fallback when no API key is configured.
"""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("engine.search")


class WebSearchEngine:
    """
    Web search integration using Tavily API.

    When TAVILY_API_KEY is configured, performs real web searches returning
    titles, URLs, and content snippets. Falls back gracefully to empty results
    when no key is set (agents then rely purely on Claude's knowledge).
    """

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._client = None
        if api_key:
            try:
                from tavily import TavilyClient

                self._client = TavilyClient(api_key=api_key)
                _logger.info("Tavily web search enabled")
            except ImportError:
                _logger.warning("tavily-python not installed; web search disabled")
            except Exception as exc:
                _logger.warning("Failed to initialize Tavily client: %s", exc)

    @property
    def is_available(self) -> bool:
        """True if the Tavily client is configured and ready."""
        return self._client is not None

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search the web for relevant results.

        Returns list of dicts with: title, url, content
        Returns empty list if Tavily is not configured or on error.
        """
        if not self._client:
            _logger.info("Web search skipped (no API key): %s", query[:100])
            return []

        try:
            _logger.info("Web search: %s (max_results=%d)", query[:100], max_results)
            response = self._client.search(query=query, max_results=max_results)
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                })
            return results
        except Exception as exc:
            _logger.warning("Web search failed for '%s': %s", query[:50], exc)
            return []

    def search_context(self, query: str, max_results: int = 5) -> str:
        """
        Search and return concatenated text snippets optimized for LLM prompts.

        Returns a formatted string of search results, or empty string on failure.
        """
        results = self.search(query, max_results=max_results)
        if not results:
            return ""

        parts = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            parts.append(f"[{title}]({url})\n{content}")

        return "\n\n---\n\n".join(parts)
