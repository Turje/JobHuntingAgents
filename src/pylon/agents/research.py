"""
ResearchAgent — deep company investigation.
Produces CompanyProfile objects with R&D approach, culture, ML use cases, hiring signals.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseSearchAgent
from pylon.config import GOOGLE_API_KEY, GOOGLE_CSE_ID, SERPER_API_KEY
from pylon.core.claude_client import ClaudeClient
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    CompanyProfile,
    ContractStatus,
    FundingStage,
    PipelineContext,
    RouterContract,
)


class ResearchAgent(BaseSearchAgent):
    """Researches companies in depth to produce CompanyProfile objects."""

    name = "research"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="research")
        self.search = WebSearchEngine(SERPER_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID)
        self.logger = logging.getLogger("agent.research")

    def run(self, context: PipelineContext) -> RouterContract:
        """Research all candidates in context. Populates context.profiles."""
        if not context.candidates:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No candidates to research",
            )

        companies_list = [
            {"name": c.name, "domain": c.domain.value, "relevance": c.relevance_reason}
            for c in context.candidates
        ]

        web_context = ""
        if self.search.is_available:
            snippets = []
            for c in context.candidates:
                snippet = self.search.search_context(
                    f"{c.name} engineering blog tech stack culture", max_results=3
                )
                if snippet:
                    snippets.append(f"### {c.name}\n{snippet}")
            web_context = "\n\n".join(snippets)

        if self._use_dspy:
            return self._run_dspy(context, companies_list, web_context)
        return self._run_claude(context, companies_list, web_context)

    def _run_dspy(
        self, context: PipelineContext, companies_list: list, web_context: str
    ) -> RouterContract:
        """Execute research via DSPy module."""
        try:
            from pylon.dspy_.modules import ResearchModule

            module = ResearchModule()
            prediction = module(
                query=context.query,
                companies_json=json.dumps(companies_list),
                web_context=web_context,
            )

            profiles = self._parse_profiles(prediction.profiles_json)
            context.profiles = profiles

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(90.0, len(profiles) * 8.0),
                critical_issues=0 if profiles else 1,
                blocking=False,
                kb_update_notes=f"Researched {len(profiles)} companies (DSPy)",
            )
        except Exception as exc:
            self.logger.error("ResearchAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Research (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, companies_list: list, web_context: str
    ) -> RouterContract:
        """Execute research via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            web_preamble = ""
            if web_context:
                web_preamble = (
                    "Here is real web search data about these companies:\n"
                    f"{web_context}\n\n"
                    "Using this real data plus your knowledge, research "
                )
            else:
                web_preamble = "Research "

            user_message = (
                f"{web_preamble}these companies for a job seeker interested in: {context.query}\n\n"
                f"Companies:\n{json.dumps(companies_list, indent=2)}\n\n"
                "For each company, return a JSON array with detailed profiles.\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            profiles = self._parse_profiles(response)
            context.profiles = profiles

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(90.0, len(profiles) * 8.0),
                critical_issues=0 if profiles else 1,
                blocking=False,
                kb_update_notes=f"Researched {len(profiles)} companies",
            )

        except Exception as exc:
            self.logger.error("ResearchAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Research failed: {exc}",
            )

    def _parse_profiles(self, response_text: str) -> list[CompanyProfile]:
        """Parse Claude's JSON into CompanyProfile objects."""
        items = self._safe_parse_json(response_text)
        profiles: list[CompanyProfile] = []

        for item in items:
            try:
                funding_str = item.get("funding_stage", "unknown")
                try:
                    funding = FundingStage(funding_str)
                except ValueError:
                    funding = FundingStage.UNKNOWN

                profiles.append(CompanyProfile(
                    company_name=item.get("company_name", "Unknown"),
                    r_and_d_approach=item.get("r_and_d_approach", ""),
                    engineering_blog=item.get("engineering_blog", ""),
                    notable_clients=item.get("notable_clients", []),
                    culture=item.get("culture", ""),
                    ml_use_cases=item.get("ml_use_cases", []),
                    funding_stage=funding,
                    hiring_signals=item.get("hiring_signals", []),
                    headquarters=item.get("headquarters", ""),
                    employee_count=item.get("employee_count", ""),
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed profile: %s", exc)
                continue

        return profiles
