"""
Simple in-memory search result cache with TTL expiry.
Keeps repeated DiscoveryAgent / ResearchAgent calls fast without external deps.
"""

from __future__ import annotations

import time
from typing import Any


class SearchCache:
    """In-memory key-value cache with per-entry TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return cached value or ``None`` if missing / expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store *value* under *key* with a TTL (default 5 minutes)."""
        expires_at = time.monotonic() + ttl_seconds
        self._store[key] = (value, expires_at)

    def clear(self) -> None:
        """Drop all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Number of entries (including potentially expired ones)."""
        return len(self._store)

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def evict_expired(self) -> int:
        """Remove all expired entries. Returns the count of evicted items."""
        now = time.monotonic()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)
