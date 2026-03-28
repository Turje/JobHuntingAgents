"""
Web search integration for CastNet.
Uses Google Custom Search API for real web search, with graceful fallback when
no API key or search engine ID is configured.
"""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("engine.search")


class WebSearchEngine:
    """
    Web search integration using Google Custom Search API.

    When GOOGLE_API_KEY and GOOGLE_CSE_ID are configured, performs real web
    searches returning titles, URLs, and content snippets. Falls back gracefully
    to empty results when keys are missing (agents then rely purely on Claude's
    knowledge).
    """

    def __init__(self, api_key: str = "", cse_id: str = "") -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        self._service = None
        if api_key and cse_id:
            try:
                from googleapiclient.discovery import build

                self._service = build("customsearch", "v1", developerKey=api_key)
                _logger.info("Google Custom Search enabled")
            except ImportError:
                _logger.warning(
                    "google-api-python-client not installed; web search disabled"
                )
            except Exception as exc:
                _logger.warning("Failed to initialize Google search: %s", exc)

    @property
    def is_available(self) -> bool:
        """True if the Google search service is configured and ready."""
        return self._service is not None

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search the web for relevant results.

        Returns list of dicts with: title, url, content
        Returns empty list if Google search is not configured or on error.
        """
        if not self._service:
            _logger.info("Web search skipped (no API key): %s", query[:100])
            return []

        try:
            _logger.info("Google search: %s (max_results=%d)", query[:100], max_results)
            results: list[dict[str, Any]] = []
            # Google CSE returns max 10 per request; paginate if needed
            fetched = 0
            start = 1
            while fetched < max_results:
                num = min(10, max_results - fetched)
                resp = (
                    self._service.cse()
                    .list(q=query, cx=self.cse_id, num=num, start=start)
                    .execute()
                )
                for item in resp.get("items", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", ""),
                    })
                fetched += num
                start += num
                # Stop if fewer items than requested (no more pages)
                if len(resp.get("items", [])) < num:
                    break
            return results[:max_results]
        except Exception as exc:
            _logger.warning("Google search failed for '%s': %s", query[:50], exc)
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
