"""
Anthropic SDK wrapper with retry logic and structured logging.
Adapted from TradeBots — used by every agent in the JobHuntingAgents pipeline.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import anthropic

from pylon.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_RETRIES, RETRY_BASE_DELAY

_RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

_FATAL_ERRORS = (
    anthropic.AuthenticationError,
    anthropic.BadRequestError,
)


class ClaudeClient:
    """
    Wrapper around the Anthropic SDK with:
    - Retry logic with exponential backoff
    - Structured logging per agent
    """

    def __init__(self, agent_name: str) -> None:
        if not ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is required but not set. Add it to your .env file."
            )
        self.agent_name = agent_name
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._logger = logging.getLogger(f"claude_client.{agent_name}")

    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """
        Make one Claude API call with retry logic.
        Returns the text content of Claude's response.
        """
        if model is None:
            model = CLAUDE_MODEL

        last_exception: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            start_time = time.monotonic()
            try:
                response = self._client.messages.create(
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
                    self.agent_name,
                    model,
                    latency_ms,
                    user_message,
                    response_text,
                )
                return response_text

            except _FATAL_ERRORS:
                raise

            except _RETRYABLE_ERRORS as exc:
                last_exception = exc
                self._logger.warning(
                    "Retry %d/%d | agent=%s | error=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    self.agent_name,
                    exc,
                )
                if attempt < MAX_RETRIES - 1:
                    backoff = RETRY_BASE_DELAY * (2**attempt)
                    time.sleep(backoff)

        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"[{self.agent_name}] MAX_RETRIES is 0, no API calls were made")
