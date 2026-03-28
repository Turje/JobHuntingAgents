"""
Web search integration for CastNet.
Primary: Serper.dev (full Google web search).
Fallback: Google Custom Search API (when Serper credits run out).
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

_logger = logging.getLogger("engine.search")

_SERPER_URL = "https://google.serper.dev/search"
_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


class WebSearchEngine:
    """
    Dual-engine web search: Serper.dev (primary) → Google CSE (fallback).

    Tries Serper first for full unrestricted Google results. If Serper fails
    (credits exhausted, rate-limited, network error), automatically falls back
    to Google Custom Search API. Returns empty results only when both fail
    or neither is configured.
    """

    def __init__(
        self,
        serper_api_key: str = "",
        google_api_key: str = "",
        google_cse_id: str = "",
    ) -> None:
        self.serper_api_key = serper_api_key
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id

    @property
    def is_available(self) -> bool:
        """True if at least one search backend is configured."""
        return bool(self.serper_api_key) or (
            bool(self.google_api_key) and bool(self.google_cse_id)
        )

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search the web. Tries Serper first, falls back to Google CSE.

        Returns list of dicts with: title, url, content
        """
        if not self.is_available:
            _logger.info("Web search skipped (no keys configured): %s", query[:100])
            return []

        # Primary: Serper.dev
        if self.serper_api_key:
            results = self._search_serper(query, max_results)
            if results is not None:
                return results
            _logger.info("Serper failed, trying Google CSE fallback")

        # Fallback: Google Custom Search
        if self.google_api_key and self.google_cse_id:
            results = self._search_google_cse(query, max_results)
            if results is not None:
                return results

        return []

    def _search_serper(self, query: str, max_results: int) -> list[dict[str, Any]] | None:
        """
        Search via Serper.dev. Returns results list on success, None on failure.
        None signals the caller to try the fallback engine.
        """
        try:
            _logger.info("Serper search: %s (max_results=%d)", query[:100], max_results)
            payload = json.dumps({"q": query, "num": min(max_results, 100)}).encode()
            req = Request(
                _SERPER_URL,
                data=payload,
                headers={
                    "X-API-KEY": self.serper_api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            results: list[dict[str, Any]] = []
            for item in data.get("organic", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                })
            return results
        except HTTPError as exc:
            _logger.warning("Serper HTTP %d for '%s': %s", exc.code, query[:50], exc)
            return None  # trigger fallback
        except (URLError, OSError) as exc:
            _logger.warning("Serper network error for '%s': %s", query[:50], exc)
            return None  # trigger fallback
        except Exception as exc:
            _logger.warning("Serper search failed for '%s': %s", query[:50], exc)
            return None  # trigger fallback

    def _search_google_cse(self, query: str, max_results: int) -> list[dict[str, Any]] | None:
        """
        Search via Google Custom Search JSON API (REST). Returns results or None.
        """
        try:
            num = min(max_results, 10)  # Google CSE caps at 10 per request
            _logger.info("Google CSE search: %s (num=%d)", query[:100], num)
            params = urlencode({
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": num,
            })
            url = f"{_GOOGLE_CSE_URL}?{params}"
            req = Request(url, method="GET")
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            results: list[dict[str, Any]] = []
            for item in data.get("items", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                })
            return results
        except HTTPError as exc:
            _logger.warning("Google CSE HTTP %d for '%s': %s", exc.code, query[:50], exc)
            return None
        except (URLError, OSError) as exc:
            _logger.warning("Google CSE network error for '%s': %s", query[:50], exc)
            return None
        except Exception as exc:
            _logger.warning("Google CSE search failed for '%s': %s", query[:50], exc)
            return None

    def search_context(self, query: str, max_results: int = 5) -> str:
        """
        Search and return concatenated text snippets optimized for LLM prompts.
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
