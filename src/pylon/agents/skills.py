"""
SkillsAgent — tech stack and skill gap analysis.
Produces SkillsAnalysis objects comparing company requirements vs user skills.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent
from pylon.config import GOOGLE_API_KEY, GOOGLE_CSE_ID
from pylon.core.claude_client import ClaudeClient
from pylon.engine.search import WebSearchEngine
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
        self.search = WebSearchEngine(GOOGLE_API_KEY, GOOGLE_CSE_ID)
        self.logger = logging.getLogger("agent.skills")

    def run(self, context: PipelineContext) -> RouterContract:
        """Analyze skills for all profiled companies. Populates context.skills."""
        if not context.profiles:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No profiles to analyze skills for",
            )

        profiles_data = [
            {
                "company_name": p.company_name,
                "ml_use_cases": p.ml_use_cases,
                "r_and_d_approach": p.r_and_d_approach,
            }
            for p in context.profiles
        ]

        web_context = ""
        if self.search.is_available:
            snippets = []
            for p in context.profiles:
                snippet = self.search.search_context(
                    f"{p.company_name} data scientist machine learning job requirements",
                    max_results=3,
                )
                if snippet:
                    snippets.append(f"### {p.company_name}\n{snippet}")
            web_context = "\n\n".join(snippets)

        if self._use_dspy:
            return self._run_dspy(context, profiles_data, web_context)
        return self._run_claude(context, profiles_data, web_context)

    def _run_dspy(
        self, context: PipelineContext, profiles_data: list, web_context: str
    ) -> RouterContract:
        """Execute skills analysis via DSPy module."""
        try:
            from pylon.dspy_.modules import SkillsModule

            module = SkillsModule()
            prediction = module(
                query=context.query,
                profiles_json=json.dumps(profiles_data),
                web_context=web_context,
            )

            analyses = self._parse_analyses(prediction.analyses_json)
            context.skills = analyses

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(analyses) * 8.0),
                critical_issues=0 if analyses else 1,
                blocking=False,
                kb_update_notes=f"Analyzed skills for {len(analyses)} companies (DSPy)",
            )
        except Exception as exc:
            self.logger.error("SkillsAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Skills analysis (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, profiles_data: list, web_context: str
    ) -> RouterContract:
        """Execute skills analysis via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            web_preamble = ""
            if web_context:
                web_preamble = (
                    "Here is real job posting and tech stack data:\n"
                    f"{web_context}\n\n"
                    "Using this real data plus your knowledge, analyze "
                )
            else:
                web_preamble = "Analyze "

            user_message = (
                f"{web_preamble}tech stacks for a job seeker interested in: {context.query}\n\n"
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
