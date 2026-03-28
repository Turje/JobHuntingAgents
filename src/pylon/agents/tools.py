"""
ToolSuggestionsAgent — suggests buildable tools/products per company to impress hiring managers.
Produces ToolSuggestion objects based on company profiles and skills analysis.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent, get_mode_hint
from pylon.config import GOOGLE_API_KEY, GOOGLE_CSE_ID, SERPER_API_KEY
from pylon.core.claude_client import ClaudeClient
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    ContractStatus,
    PipelineContext,
    RouterContract,
    ToolSuggestion,
)


class ToolSuggestionsAgent(BaseAnalysisAgent):
    """Suggests buildable tools/products to impress target companies."""

    name = "tools"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="tools")
        self.search = WebSearchEngine(SERPER_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID)
        self.logger = logging.getLogger("agent.tools")

    def run(self, context: PipelineContext) -> RouterContract:
        """Suggest tools for all profiled companies. Populates context.tools."""
        if not context.profiles:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No profiles to suggest tools for",
            )

        companies_data = []
        for p in context.profiles:
            entry = {
                "company_name": p.company_name,
                "ml_use_cases": p.ml_use_cases,
                "r_and_d_approach": p.r_and_d_approach,
                "culture": p.culture,
                "hiring_signals": p.hiring_signals,
            }
            # Enrich with skills data if available
            sk = next((s for s in context.skills if s.company_name == p.company_name), None)
            if sk:
                entry["tools_used"] = sk.tools_used
                entry["ml_frameworks"] = sk.ml_frameworks
                entry["cloud_platform"] = sk.cloud_platform
            companies_data.append(entry)

        # Tools agent relies on profile + skills data already gathered —
        # no additional web searches needed (saves API calls for free tier)
        web_context = ""

        if self._use_dspy:
            return self._run_dspy(context, companies_data, web_context)
        return self._run_claude(context, companies_data, web_context)

    def _run_dspy(
        self, context: PipelineContext, companies_data: list, web_context: str
    ) -> RouterContract:
        """Execute tool suggestions via DSPy module."""
        try:
            from pylon.dspy_.modules import ToolSuggestionsModule

            module = ToolSuggestionsModule()
            prediction = module(
                query=context.query,
                companies_json=json.dumps(companies_data),
                web_context=web_context,
            )

            suggestions = self._parse_suggestions(prediction.suggestions_json)
            context.tools = suggestions

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(suggestions) * 5.0),
                critical_issues=0 if suggestions else 1,
                blocking=False,
                kb_update_notes=f"Suggested {len(suggestions)} tools (DSPy)",
            )
        except Exception as exc:
            self.logger.error("ToolSuggestionsAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Tool suggestions (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, companies_data: list, web_context: str
    ) -> RouterContract:
        """Execute tool suggestions via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            web_preamble = ""
            if web_context:
                web_preamble = (
                    "Here is real data about these companies' engineering challenges:\n"
                    f"{web_context}\n\n"
                    "Using this real data plus your knowledge, suggest "
                )
            else:
                web_preamble = "Suggest "

            mode_hint = get_mode_hint(self.name, context)
            user_message = (
                f"{web_preamble}buildable tools for a job seeker interested in: {context.query}\n\n"
                f"Company data:\n{json.dumps(companies_data, indent=2)}\n\n"
                f"{mode_hint}\n"
                "For each company, suggest up to 5 tools/products/demos they could build "
                "to impress hiring managers. Return a JSON array.\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            suggestions = self._parse_suggestions(response)
            context.tools = suggestions

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(suggestions) * 5.0),
                critical_issues=0 if suggestions else 1,
                blocking=False,
                kb_update_notes=f"Suggested {len(suggestions)} tools",
            )

        except Exception as exc:
            self.logger.error("ToolSuggestionsAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Tool suggestions failed: {exc}",
            )

    def _parse_suggestions(self, response_text: str) -> list[ToolSuggestion]:
        """Parse Claude's JSON into ToolSuggestion objects."""
        items = self._safe_parse_json(response_text)
        suggestions: list[ToolSuggestion] = []

        for item in items:
            try:
                suggestions.append(ToolSuggestion(
                    company_name=item.get("company_name", "Unknown"),
                    tool_name=item.get("tool_name", ""),
                    description=item.get("description", ""),
                    why_impressive=item.get("why_impressive", ""),
                    estimated_revenue_impact=item.get("estimated_revenue_impact", ""),
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed tool suggestion: %s", exc)
                continue

        return suggestions
