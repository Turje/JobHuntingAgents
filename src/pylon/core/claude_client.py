"""
LLM client wrapper with retry logic and structured logging.
Supports Google Gemini (default, free) and Anthropic Claude backends.
Used by every agent in the CastNet pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from pylon.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
)

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class ClaudeClient:
    """
    LLM wrapper with retry logic. Dispatches to Gemini or Claude
    based on LLM_PROVIDER config. Keeps the name 'ClaudeClient' for
    backwards compatibility — all agents use this interface.
    """

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self._provider = LLM_PROVIDER
        self._logger = logging.getLogger(f"llm_client.{agent_name}")

        if self._provider == "gemini":
            if not GEMINI_API_KEY:
                raise EnvironmentError(
                    "GEMINI_API_KEY is required when LLM_PROVIDER=gemini. "
                    "Add it to your .env file."
                )
        elif self._provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise EnvironmentError(
                    "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
                    "Add it to your .env file."
                )
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self._provider}")

    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> str:
        """
        Make one LLM call with retry logic.
        Returns the text content of the response.
        """
        if self._provider == "gemini":
            return self._call_gemini(system_prompt, user_message, model, max_tokens, temperature)
        return self._call_anthropic(system_prompt, user_message, model, max_tokens, temperature)

    def _call_gemini(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call Google Gemini via REST API."""
        if model is None:
            model = GEMINI_MODEL

        last_exception: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            start_time = time.monotonic()
            try:
                url = f"{_GEMINI_URL}/{model}:generateContent?key={GEMINI_API_KEY}"
                payload = json.dumps({
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_message}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                }).encode()

                req = Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())

                latency_ms = int((time.monotonic() - start_time) * 1000)

                # Extract text from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError(f"[{self.agent_name}] Gemini returned no candidates")

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError(f"[{self.agent_name}] Gemini returned empty content")

                response_text = parts[0].get("text", "")
                if not response_text:
                    raise ValueError(f"[{self.agent_name}] Gemini returned empty text")

                self._logger.info(
                    "Gemini call | agent=%s | model=%s | latency=%dms | "
                    "input_preview=%.100s | output_preview=%.100s",
                    self.agent_name, model, latency_ms, user_message, response_text,
                )
                return response_text

            except HTTPError as exc:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                if exc.code in (401, 403):
                    raise
                last_exception = exc
                self._logger.warning(
                    "Retry %d/%d | agent=%s | HTTP %d | latency=%dms",
                    attempt + 1, MAX_RETRIES, self.agent_name, exc.code, latency_ms,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

            except (URLError, OSError) as exc:
                last_exception = exc
                self._logger.warning(
                    "Retry %d/%d | agent=%s | error=%s",
                    attempt + 1, MAX_RETRIES, self.agent_name, exc,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"[{self.agent_name}] MAX_RETRIES is 0, no API calls were made")

    def _call_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call Anthropic Claude API."""
        import anthropic

        if model is None:
            model = CLAUDE_MODEL

        last_exception: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            start_time = time.monotonic()
            try:
                response = self._anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    temperature=temperature,
                )
                latency_ms = int((time.monotonic() - start_time) * 1000)

                if not response.content:
                    raise ValueError(f"[{self.agent_name}] Claude returned empty content")

                response_text = response.content[0].text
                self._logger.info(
                    "Claude call | agent=%s | model=%s | latency=%dms | "
                    "input_preview=%.100s | output_preview=%.100s",
                    self.agent_name, model, latency_ms, user_message, response_text,
                )
                return response_text

            except (anthropic.AuthenticationError, anthropic.BadRequestError):
                raise

            except (anthropic.APIConnectionError, anthropic.RateLimitError,
                    anthropic.InternalServerError) as exc:
                last_exception = exc
                self._logger.warning(
                    "Retry %d/%d | agent=%s | error=%s",
                    attempt + 1, MAX_RETRIES, self.agent_name, exc,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"[{self.agent_name}] MAX_RETRIES is 0, no API calls were made")
