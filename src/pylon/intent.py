"""
7-priority intent classification for job-hunting queries.
Adapted from 21Agents intent.py — keyword patterns changed to job-hunting terms.
"""

from __future__ import annotations

import re

from pylon.models import IndustryDomain, Intent, IntentPriority

# ---------------------------------------------------------------------------
# Keyword patterns per priority
# ---------------------------------------------------------------------------

_EMERGENCY_PATTERNS = re.compile(
    r"\b(stop|halt|cancel|undo|abort|emergency|pause|rollback)\b", re.IGNORECASE
)

_DISCOVER_PATTERNS = re.compile(
    r"\b(find|discover|search|look\s*for|companies|startups|firms|identify|explore)\b",
    re.IGNORECASE,
)

_RESEARCH_PATTERNS = re.compile(
    r"\b(research|investigate|deep\s*dive|analyze|profile|background|info\s*on|learn\s*about)\b",
    re.IGNORECASE,
)

_SKILLS_PATTERNS = re.compile(
    r"\b(skills|tech\s*stack|tools|frameworks|gap|alignment|qualify|requirements)\b",
    re.IGNORECASE,
)

_CONTACT_PATTERNS = re.compile(
    r"\b(contact|reach\s*out|who|cto|founder|head\s*of|email|linkedin|decision\s*maker)\b",
    re.IGNORECASE,
)

_OUTREACH_PATTERNS = re.compile(
    r"\b(outreach|email|draft|write|cold\s*email|message|cover\s*letter|pitch)\b",
    re.IGNORECASE,
)

_REVIEW_PATTERNS = re.compile(
    r"\b(review|show|status|progress|export|excel|report|summary|results|list)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Industry domain detection
# ---------------------------------------------------------------------------

_DOMAIN_PATTERNS: list[tuple[re.Pattern, IndustryDomain]] = [
    (re.compile(r"\b(football|soccer|sports?|athletic|premier\s*league|fifa|nba|nfl)\b", re.I), IndustryDomain.SPORTS_TECH),
    (re.compile(r"\b(fintech|banking|trading|finance|payment|crypto|defi)\b", re.I), IndustryDomain.FINTECH),
    (re.compile(r"\b(health|medical|biotech|pharma|clinical|healthcare)\b", re.I), IndustryDomain.HEALTH_TECH),
    (re.compile(r"\b(edu|education|learning|teaching|school|university|edtech)\b", re.I), IndustryDomain.EDTECH),
    (re.compile(r"\b(gaming|game|esports|play|unity|unreal)\b", re.I), IndustryDomain.GAMING),
    (re.compile(r"\b(ecommerce|retail|shop|marketplace|amazon)\b", re.I), IndustryDomain.ECOMMERCE),
    (re.compile(r"\b(climate|green|sustain|carbon|renewable|energy)\b", re.I), IndustryDomain.CLIMATE_TECH),
    (re.compile(r"\b(media|news|content|streaming|entertainment|video)\b", re.I), IndustryDomain.MEDIA),
]

# ---------------------------------------------------------------------------
# Swarm detection
# ---------------------------------------------------------------------------

_SWARM_PATTERNS = re.compile(
    r"\b(comprehensive|thorough|deep\s*dive|all\s*companies|exhaustive|complete|every)\b",
    re.IGNORECASE,
)


def _detect_domain(query: str) -> IndustryDomain:
    """Detect industry domain from query text."""
    for pattern, domain in _DOMAIN_PATTERNS:
        if pattern.search(query):
            return domain
    return IndustryDomain.GENERAL


def classify_intent(query: str) -> Intent:
    """
    Classify a user query into a prioritized Intent.
    Returns the highest-priority matching intent.
    """
    query = query.strip()
    if not query:
        return Intent(priority=IntentPriority.REVIEW, raw_query=query)

    domain = _detect_domain(query)
    swarm_worthy = bool(_SWARM_PATTERNS.search(query))

    # Priority order: check highest priority first
    if _EMERGENCY_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.EMERGENCY,
            domain=domain,
            raw_query=query,
            swarm_worthy=False,
        )

    if _DISCOVER_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.DISCOVER,
            domain=domain,
            raw_query=query,
            swarm_worthy=swarm_worthy,
        )

    if _RESEARCH_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.RESEARCH,
            domain=domain,
            raw_query=query,
            swarm_worthy=swarm_worthy,
        )

    if _SKILLS_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.SKILLS,
            domain=domain,
            raw_query=query,
            swarm_worthy=False,
        )

    if _CONTACT_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.CONTACT,
            domain=domain,
            raw_query=query,
            swarm_worthy=False,
        )

    if _OUTREACH_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.OUTREACH,
            domain=domain,
            raw_query=query,
            swarm_worthy=False,
        )

    if _REVIEW_PATTERNS.search(query):
        return Intent(
            priority=IntentPriority.REVIEW,
            domain=domain,
            raw_query=query,
            swarm_worthy=False,
        )

    # Default: treat as discovery
    return Intent(
        priority=IntentPriority.DISCOVER,
        domain=domain,
        raw_query=query,
        swarm_worthy=swarm_worthy,
    )
