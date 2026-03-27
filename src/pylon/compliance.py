"""
Compliance module — rate limits, GDPR, email etiquette.
Loads rules from config/compliance/default.yaml.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pylon.config import load_compliance

_logger = logging.getLogger("compliance")


class ComplianceChecker:
    """Checks actions against compliance rules loaded from YAML config."""

    def __init__(self) -> None:
        self._rules = load_compliance()
        self._daily_email_count = 0
        self._company_contact_log: dict[str, datetime] = {}  # company -> last contact time

    @property
    def max_emails_per_company_per_week(self) -> int:
        return self._rules.get("rate_limits", {}).get("max_emails_per_company_per_week", 1)

    @property
    def max_outreach_per_day(self) -> int:
        return self._rules.get("rate_limits", {}).get("max_outreach_per_day", 10)

    @property
    def cooldown_days(self) -> int:
        return self._rules.get("rate_limits", {}).get("cooldown_days_between_contacts", 7)

    @property
    def forbidden_words(self) -> list[str]:
        return self._rules.get("email_etiquette", {}).get("forbidden_words", [])

    @property
    def max_body_words(self) -> int:
        return self._rules.get("email_etiquette", {}).get("max_body_words", 300)

    def can_send_email(self, company_name: str) -> tuple[bool, str]:
        """Check if we can send an email to this company. Returns (allowed, reason)."""
        if self._daily_email_count >= self.max_outreach_per_day:
            return False, f"Daily email limit reached ({self.max_outreach_per_day})"

        if company_name in self._company_contact_log:
            last_contact = self._company_contact_log[company_name]
            days_since = (datetime.now(timezone.utc) - last_contact).days
            if days_since < self.cooldown_days:
                return False, f"Cooldown active for {company_name} ({days_since}/{self.cooldown_days} days)"

        return True, "OK"

    def check_email_content(self, subject: str, body: str) -> list[str]:
        """Check email content against etiquette rules. Returns list of violations."""
        violations: list[str] = []
        max_subject = self._rules.get("email_etiquette", {}).get("max_subject_length", 80)
        if len(subject) > max_subject:
            violations.append(f"Subject too long ({len(subject)} > {max_subject} chars)")

        word_count = len(body.split())
        if word_count > self.max_body_words:
            violations.append(f"Body too long ({word_count} > {self.max_body_words} words)")

        body_lower = body.lower()
        for word in self.forbidden_words:
            if word.lower() in body_lower:
                violations.append(f"Forbidden word found: '{word}'")

        return violations

    def record_email_sent(self, company_name: str) -> None:
        """Record that an email was sent to a company."""
        self._daily_email_count += 1
        self._company_contact_log[company_name] = datetime.now(timezone.utc)
        _logger.info(
            "Email recorded for %s (daily count: %d)", company_name, self._daily_email_count
        )

    def reset_daily_counts(self) -> None:
        """Reset daily email counter (call at midnight)."""
        self._daily_email_count = 0
