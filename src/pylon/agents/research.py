"""
ResearchAgent — deep company investigation.
Produces CompanyProfile objects with R&D approach, culture, ML use cases, hiring signals.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseSearchAgent
from pylon.core.claude_client import ClaudeClient
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
        self.logger = logging.getLogger("agent.research")

    def run(self, context: PipelineContext) -> RouterContract:
        """Research all candidates in context. Populates context.profiles."""
        try:
            if not context.candidates:
                return RouterContract(
                    status=ContractStatus.EXECUTED,
                    confidence=0.0,
                    kb_update_notes="No candidates to research",
                )

            system_prompt = self._load_brain()
            companies_list = [
                {"name": c.name, "domain": c.domain.value, "relevance": c.relevance_reason}
                for c in context.candidates
            ]

            user_message = (
                f"Research these companies for a job seeker interested in: {context.query}\n\n"
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
