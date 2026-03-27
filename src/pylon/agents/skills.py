"""
SkillsAgent — tech stack and skill gap analysis.
Produces SkillsAnalysis objects comparing company requirements vs user skills.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent
from pylon.core.claude_client import ClaudeClient
from pylon.models import (
    ContractStatus,
    PipelineContext,
    RouterContract,
    SkillsAnalysis,
)


class SkillsAgent(BaseAnalysisAgent):
    """Analyzes tech stacks and identifies skill gaps."""

    name = "skills"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="skills")
        self.logger = logging.getLogger("agent.skills")

    def run(self, context: PipelineContext) -> RouterContract:
        """Analyze skills for all profiled companies. Populates context.skills."""
        try:
            if not context.profiles:
                return RouterContract(
                    status=ContractStatus.EXECUTED,
                    confidence=0.0,
                    kb_update_notes="No profiles to analyze skills for",
                )

            system_prompt = self._load_brain()
            profiles_data = [
                {
                    "company_name": p.company_name,
                    "ml_use_cases": p.ml_use_cases,
                    "r_and_d_approach": p.r_and_d_approach,
                }
                for p in context.profiles
            ]

            user_message = (
                f"Analyze tech stacks for a job seeker interested in: {context.query}\n\n"
                f"Company profiles:\n{json.dumps(profiles_data, indent=2)}\n\n"
                "For each company, return a JSON array with skills analysis.\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            analyses = self._parse_analyses(response)
            context.skills = analyses

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(analyses) * 8.0),
                critical_issues=0 if analyses else 1,
                blocking=False,
                kb_update_notes=f"Analyzed skills for {len(analyses)} companies",
            )

        except Exception as exc:
            self.logger.error("SkillsAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Skills analysis failed: {exc}",
            )

    def _parse_analyses(self, response_text: str) -> list[SkillsAnalysis]:
        """Parse Claude's JSON into SkillsAnalysis objects."""
        items = self._safe_parse_json(response_text)
        analyses: list[SkillsAnalysis] = []

        for item in items:
            try:
                score = item.get("alignment_score", 0.5)
                try:
                    score = max(0.0, min(1.0, float(score)))
                except (ValueError, TypeError):
                    score = 0.5

                analyses.append(SkillsAnalysis(
                    company_name=item.get("company_name", "Unknown"),
                    tools_used=item.get("tools_used", []),
                    ml_frameworks=item.get("ml_frameworks", []),
                    cloud_platform=item.get("cloud_platform", ""),
                    skills_to_learn=item.get("skills_to_learn", []),
                    alignment_score=score,
                    gap_analysis=item.get("gap_analysis", ""),
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed skills analysis: %s", exc)
                continue

        return analyses
