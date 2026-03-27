"""
Web search integration for JobHuntingAgents.
Provides search capabilities for company discovery and research.
"""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("engine.search")


class WebSearchEngine:
    """
    Web search integration.
    Currently delegates to Claude's knowledge; can be extended with
    Serper, SerpAPI, or Google Custom Search API.
    """

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search the web for relevant results.

        Returns list of dicts with: title, url, snippet
        Currently a stub — returns empty list.
        Integrate with a search API for production use.
        """
        _logger.info("Web search: %s (max_results=%d)", query[:100], max_results)
        # Stub: Claude's knowledge is used directly in agents
        # To enable web search, integrate Serper/SerpAPI here
        return []
