"""
ResumeAgent — tailors resume summaries and bullets per company.
Produces ResumeVersion objects customized to each target company.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent
from pylon.core.claude_client import ClaudeClient
from pylon.models import (
    ContractStatus,
    PipelineContext,
    ResumeVersion,
    RouterContract,
)


class ResumeAgent(BaseAnalysisAgent):
    """Tailors resume content per company based on profiles and skills analysis."""

    name = "resume"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="resume")
        self.logger = logging.getLogger("agent.resume")

    def run(self, context: PipelineContext) -> RouterContract:
        """Tailor resumes for all companies. Populates context.resumes."""
        if not context.candidates:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No companies to tailor resumes for",
            )

        companies_data = []
        for c in context.candidates:
            entry = {"company_name": c.name, "relevance": c.relevance_reason}
            profile = next((p for p in context.profiles if p.company_name == c.name), None)
            if profile:
                entry["ml_use_cases"] = profile.ml_use_cases
                entry["culture"] = profile.culture
            skill = next((s for s in context.skills if s.company_name == c.name), None)
            if skill:
                entry["tools_used"] = skill.tools_used
                entry["alignment_score"] = skill.alignment_score
            companies_data.append(entry)

        if self._use_dspy:
            return self._run_dspy(context, companies_data)
        return self._run_claude(context, companies_data)

    def _run_dspy(
        self, context: PipelineContext, companies_data: list
    ) -> RouterContract:
        """Execute resume tailoring via DSPy module."""
        try:
            from pylon.dspy_.modules import ResumeModule

            module = ResumeModule()
            prediction = module(
                query=context.query,
                companies_json=json.dumps(companies_data),
            )

            resumes = self._parse_resumes(prediction.resumes_json)
            context.resumes = resumes

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(resumes) * 8.0),
                critical_issues=0 if resumes else 1,
                blocking=False,
                kb_update_notes=f"Tailored {len(resumes)} resume versions (DSPy)",
            )
        except Exception as exc:
            self.logger.error("ResumeAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Resume tailoring (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, companies_data: list
    ) -> RouterContract:
        """Execute resume tailoring via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            user_message = (
                f"Tailor resume content for a job seeker interested in: {context.query}\n\n"
                f"Target companies:\n{json.dumps(companies_data, indent=2)}\n\n"
                "For each company, return a JSON array with tailored resume content.\n"
                "Fields: company_name, tailored_summary, emphasis_areas (list), "
                "highlighted_projects (list), tailored_bullets (list)\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            resumes = self._parse_resumes(response)
            context.resumes = resumes

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(resumes) * 8.0),
                critical_issues=0 if resumes else 1,
                blocking=False,
                kb_update_notes=f"Tailored {len(resumes)} resume versions",
            )

        except Exception as exc:
            self.logger.error("ResumeAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Resume tailoring failed: {exc}",
            )

    def _parse_resumes(self, response_text: str) -> list[ResumeVersion]:
        """Parse Claude's JSON into ResumeVersion objects."""
        items = self._safe_parse_json(response_text)
        resumes: list[ResumeVersion] = []

        for item in items:
            try:
                resumes.append(ResumeVersion(
                    company_name=item.get("company_name", "Unknown"),
                    tailored_summary=item.get("tailored_summary", ""),
                    emphasis_areas=item.get("emphasis_areas", []),
                    highlighted_projects=item.get("highlighted_projects", []),
                    tailored_bullets=item.get("tailored_bullets", []),
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed resume: %s", exc)
                continue

        return resumes
