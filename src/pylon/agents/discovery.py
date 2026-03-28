"""
DiscoveryAgent — converts free-text queries into a list of CompanyCandidate objects.
First stage of the CastNet pipeline.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseSearchAgent
from pylon.config import GOOGLE_API_KEY, GOOGLE_CSE_ID, MAX_COMPANIES_PER_SEARCH, SERPER_API_KEY
from pylon.core.claude_client import ClaudeClient
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyCandidate,
    ContractStatus,
    IndustryDomain,
    PipelineContext,
    RouterContract,
)


class DiscoveryAgent(BaseSearchAgent):
    """Discovers companies matching a user's free-text query and interests."""

    name = "discovery"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="discovery")
        self.search = WebSearchEngine(SERPER_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID)
        self.logger = logging.getLogger("agent.discovery")

    def run(self, context: PipelineContext) -> RouterContract:
        """
        Discover companies from the user's query.
        Populates context.candidates and returns a RouterContract.
        """
        domain_hint = ""
        if context.intent and context.intent.domain != IndustryDomain.GENERAL:
            domain_hint = f"\nFocus on the {context.intent.domain.value} industry."

        web_context = ""
        if self.search.is_available:
            web_context = self.search.search_context(
                f"{context.query} companies hiring careers", max_results=10
            )

        if self._use_dspy:
            return self._run_dspy(context, domain_hint, web_context)
        return self._run_claude(context, domain_hint, web_context)

    def _run_dspy(
        self, context: PipelineContext, domain_hint: str, web_context: str
    ) -> RouterContract:
        """Execute discovery via DSPy module."""
        try:
            from pylon.dspy_.modules import DiscoveryModule

            module = DiscoveryModule()
            prediction = module(
                query=context.query,
                domain_hint=domain_hint,
                web_context=web_context,
                max_companies=MAX_COMPANIES_PER_SEARCH,
            )

            candidates = self._parse_candidates(prediction.companies_json)
            context.candidates = candidates

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(90.0, len(candidates) * 7.0),
                critical_issues=0 if candidates else 1,
                blocking=len(candidates) == 0,
                kb_update_notes=f"Discovered {len(candidates)} companies (DSPy) for: {context.query[:50]}",
            )
        except Exception as exc:
            self.logger.error("DiscoveryAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Discovery (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, domain_hint: str, web_context: str
    ) -> RouterContract:
        """Execute discovery via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            web_preamble = ""
            if web_context:
                web_preamble = (
                    "Here is real web search data about this topic:\n"
                    f"{web_context}\n\n"
                    "Using this real data plus your knowledge, "
                )
            else:
                web_preamble = "Using your knowledge, "

            user_message = (
                f"User query: {context.query}\n"
                f"{domain_hint}\n\n"
                f"{web_preamble}"
                f"find up to {MAX_COMPANIES_PER_SEARCH} companies that match this query.\n"
                "Return a JSON array of objects with these fields:\n"
                '- "name": company name\n'
                '- "domain": industry domain (sports_tech, fintech, health_tech, edtech, gaming, ecommerce, climate_tech, media, general)\n'
                '- "relevance_reason": why this company matches the query\n'
                '- "website": company website URL\n'
                '- "confidence": 0.0 to 1.0 how well it matches\n\n'
                "Return ONLY the JSON array. No other text."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            candidates = self._parse_candidates(response)
            context.candidates = candidates

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(90.0, len(candidates) * 7.0),
                critical_issues=0 if candidates else 1,
                blocking=len(candidates) == 0,
                kb_update_notes=f"Discovered {len(candidates)} companies for: {context.query[:50]}",
            )

        except Exception as exc:
            self.logger.error("DiscoveryAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Discovery failed: {exc}",
            )

    def _parse_candidates(self, response_text: str) -> list[CompanyCandidate]:
        """Parse Claude's JSON into CompanyCandidate objects."""
        items = self._safe_parse_json(response_text)
        candidates: list[CompanyCandidate] = []
        for item in items:
            try:
                domain_str = item.get("domain", "general")
                try:
                    domain = IndustryDomain(domain_str)
                except ValueError:
                    domain = IndustryDomain.GENERAL

                confidence = item.get("confidence", 0.5)
                try:
                    confidence = max(0.0, min(1.0, float(confidence)))
                except (ValueError, TypeError):
                    confidence = 0.5

                candidates.append(CompanyCandidate(
                    name=item.get("name", "Unknown"),
                    domain=domain,
                    relevance_reason=item.get("relevance_reason", ""),
                    website=item.get("website", ""),
                    confidence=confidence,
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed candidate: %s", exc)
                continue

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates[:MAX_COMPANIES_PER_SEARCH]
