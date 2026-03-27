"""
OutreachAgent — drafts personalized cold outreach emails.
Produces OutreachDraft objects with subject, body, and personalization notes.
"""

from __future__ import annotations

import json
import logging

from pylon.agents.base import BaseAnalysisAgent
from pylon.core.claude_client import ClaudeClient
from pylon.models import (
    ContractStatus,
    OutreachDraft,
    PipelineContext,
    RouterContract,
)


class OutreachAgent(BaseAnalysisAgent):
    """Drafts personalized cold emails for each company contact."""

    name = "outreach"

    def __init__(self) -> None:
        self.client = ClaudeClient(agent_name="outreach")
        self.logger = logging.getLogger("agent.outreach")

    def run(self, context: PipelineContext) -> RouterContract:
        """Draft outreach emails. Populates context.drafts."""
        if not context.contacts:
            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=0.0,
                kb_update_notes="No contacts to draft emails for",
            )

        contacts_data = []
        for ct in context.contacts:
            entry = {
                "company_name": ct.company_name,
                "contact_name": ct.name,
                "title": ct.title,
            }
            profile = next((p for p in context.profiles if p.company_name == ct.company_name), None)
            if profile:
                entry["ml_use_cases"] = profile.ml_use_cases
                entry["culture"] = profile.culture
            resume = next((r for r in context.resumes if r.company_name == ct.company_name), None)
            if resume:
                entry["tailored_summary"] = resume.tailored_summary
            contacts_data.append(entry)

        if self._use_dspy:
            return self._run_dspy(context, contacts_data)
        return self._run_claude(context, contacts_data)

    def _run_dspy(
        self, context: PipelineContext, contacts_data: list
    ) -> RouterContract:
        """Execute outreach drafting via DSPy module."""
        try:
            from pylon.dspy_.modules import OutreachModule

            module = OutreachModule()
            prediction = module(
                query=context.query,
                contacts_json=json.dumps(contacts_data),
            )

            drafts = self._parse_drafts(prediction.drafts_json)
            context.drafts = drafts

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(drafts) * 10.0),
                critical_issues=0 if drafts else 1,
                blocking=False,
                kb_update_notes=f"Drafted {len(drafts)} outreach emails (DSPy)",
            )
        except Exception as exc:
            self.logger.error("OutreachAgent._run_dspy failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Outreach drafting (DSPy) failed: {exc}",
            )

    def _run_claude(
        self, context: PipelineContext, contacts_data: list
    ) -> RouterContract:
        """Execute outreach drafting via direct ClaudeClient call."""
        try:
            system_prompt = self._load_brain()

            user_message = (
                f"Draft cold outreach emails for: {context.query}\n\n"
                f"Contacts with company context:\n{json.dumps(contacts_data, indent=2)}\n\n"
                "For each contact, return a JSON array with email drafts.\n"
                "Fields: company_name, contact_name, subject, body, "
                "personalization_notes, template_used\n"
                "Rules: max 300 words body, no 'urgent'/'act now'/'guaranteed', "
                "personalized opening, clear call-to-action.\n"
                "Return ONLY the JSON array."
            )

            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
            )

            drafts = self._parse_drafts(response)
            context.drafts = drafts

            return RouterContract(
                status=ContractStatus.EXECUTED,
                confidence=min(85.0, len(drafts) * 10.0),
                critical_issues=0 if drafts else 1,
                blocking=False,
                kb_update_notes=f"Drafted {len(drafts)} outreach emails",
            )

        except Exception as exc:
            self.logger.error("OutreachAgent.run failed: %s", exc)
            return RouterContract(
                status=ContractStatus.BLOCKED,
                confidence=0.0,
                critical_issues=1,
                blocking=True,
                kb_update_notes=f"Outreach drafting failed: {exc}",
            )

    def _parse_drafts(self, response_text: str) -> list[OutreachDraft]:
        """Parse Claude's JSON into OutreachDraft objects."""
        items = self._safe_parse_json(response_text)
        drafts: list[OutreachDraft] = []

        for item in items:
            try:
                drafts.append(OutreachDraft(
                    company_name=item.get("company_name", "Unknown"),
                    contact_name=item.get("contact_name", ""),
                    subject=item.get("subject", ""),
                    body=item.get("body", ""),
                    personalization_notes=item.get("personalization_notes", ""),
                    template_used=item.get("template_used", "cold"),
                ))
            except Exception as exc:
                self.logger.warning("Skipping malformed draft: %s", exc)
                continue

        return drafts
