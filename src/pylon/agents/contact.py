"""
ContactAgent — finds decision-makers at target companies.
Produces ContactInfo objects with names, titles, emails, LinkedIn URLs.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent
from pylon.core.claude_client import ClaudeClient
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
        self.logger = logging.getLogger("agent.contact")

    def run(self, context: PipelineContext) -> RouterContract:
        """Find contacts for all candidates. Populates context.contacts."""
        try:
            companies = context.profiles or [
                type("P", (), {"company_name": c.name})() for c in context.candidates
            ]
            if not companies:
                return RouterContract(
                    status=ContractStatus.EXECUTED,
                    confidence=0.0,
                    kb_update_notes="No companies to find contacts for",
                )

            system_prompt = self._load_brain()
            companies_data = [
                {"company_name": getattr(c, "company_name", "Unknown")}
                for c in companies
            ]

            user_message = (
                f"Find decision-makers for DS/ML hiring at these companies.\n"
                f"Context: {context.query}\n\n"
                f"Companies:\n{json.dumps(companies_data, indent=2)}\n\n"
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
