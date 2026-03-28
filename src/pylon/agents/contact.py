"""
ContactAgent — finds decision-makers at target companies.
Produces ContactInfo objects with names, titles, emails, LinkedIn URLs.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent, get_mode_hint
from pylon.config import GOOGLE_API_KEY, GOOGLE_CSE_ID, SERPER_API_KEY
from pylon.core.claude_client import ClaudeClient
from pylon.engine.search import WebSearchEngine
from pylon.models import (
    ContactInfo,
    ContractStatus,
    PipelineContext,
    RouterContract,
)


class ContactAgent(BaseAnalysisAgent):
    """Finds key contacts (CTO, Head of DS, etc.) at target companies."""

    name = "contact"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="contact")
        self.search = WebSearchEngine(SERPER_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID)
        self.logger = logging.getLogger("agent.contact")

    def run(self, context: PipelineContext) -> RouterContract:
        """Find contacts for all candidates. Populates context.contacts."""
        companies = context.profiles or [
            type("P", (), {"company_name": c.name})() for c in context.candidates
        ]
        if not companies:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No companies to find contacts for",
            )

        companies_data = [
            {"company_name": getattr(c, "company_name", "Unknown")}
            for c in companies
        ]

        # Contact agent relies on profile data already gathered by Research —
        # no additional web searches needed (saves API calls for free tier)
        web_context = ""

        if self._use_dspy:
            return self._run_dspy(context, companies_data, web_context)
        return self._run_claude(context, companies_data, web_context)

    def _run_dspy(
        self, context: PipelineContext, companies_data: list, web_context: str
    ) -> RouterContract:
        """Execute contact search via DSPy module."""
        try:
            from pylon.dspy_.modules import ContactModule

            module = ContactModule()
            prediction = module(
                query=context.query,
                companies_json=json.dumps(companies_data),
                web_context=web_context,
            )

            contacts = self._parse_contacts(prediction.contacts_json)
            context.contacts = contacts

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(contacts) * 10.0),
                critical_issues=0 if contacts else 1,
                blocking=False,
                kb_update_notes=f"Found {len(contacts)} contacts (DSPy)",
            )
        except Exception as exc:
            self.logger.error("ContactAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Contact search (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, companies_data: list, web_context: str
    ) -> RouterContract:
        """Execute contact search via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            web_preamble = ""
            if web_context:
                web_preamble = (
                    "Here is real web data about decision-makers at these companies:\n"
                    f"{web_context}\n\n"
                    "Using this real data plus your knowledge, find "
                )
            else:
                web_preamble = "Find "

            mode_hint = get_mode_hint(self.name, context)
            user_message = (
                f"{web_preamble}decision-makers for hiring at these companies.\n"
                f"The user is looking for: {context.query}\n\n"
                f"Companies:\n{json.dumps(companies_data, indent=2)}\n\n"
                f"{mode_hint}\n"
                "Return a JSON array with one contact per company.\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            contacts = self._parse_contacts(response)
            context.contacts = contacts

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(contacts) * 10.0),
                critical_issues=0 if contacts else 1,
                blocking=False,
                kb_update_notes=f"Found {len(contacts)} contacts",
            )

        except Exception as exc:
            self.logger.error("ContactAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Contact search failed: {exc}",
            )

    def _parse_contacts(self, response_text: str) -> list[ContactInfo]:
        """Parse Claude's JSON into ContactInfo objects."""
        items = self._safe_parse_json(response_text)
        contacts: list[ContactInfo] = []

        for item in items:
            try:
                confidence = item.get("confidence", 0.5)
                try:
                    confidence = max(0.0, min(1.0, float(confidence)))
                except (ValueError, TypeError):
                    confidence = 0.5

                contacts.append(ContactInfo(
                    company_name=item.get("company_name", "Unknown"),
                    name=item.get("name", "Unknown"),
                    title=item.get("title", ""),
                    email=item.get("email", ""),
                    linkedin_url=item.get("linkedin_url", ""),
                    notes=item.get("notes", ""),
                    confidence=confidence,
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed contact: %s", exc)
                continue

        return contacts
