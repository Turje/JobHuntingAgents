"""
Evaluation metrics for MIPROv2 optimization — one metric per agent.
Each returns a float in [0, 1].
"""

from __future__ import annotations

import json
from typing import Any


def _safe_parse(text: str) -> list[dict[str, Any]]:
    """Parse JSON text, return empty list on failure."""
    if not text:
        return []
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else [result] if isinstance(result, dict) else []
    except (json.JSONDecodeError, ValueError):
        return []


# ---------------------------------------------------------------------------
# Discovery metric
# ---------------------------------------------------------------------------


def discovery_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score discovery output: non-empty (0.3), name overlap (0.3),
    valid confidence (0.2), specific domains (0.2)."""
    output = getattr(prediction, "companies_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.3  # non-empty

    # Name overlap with expected (if available)
    expected_names = set()
    if hasattr(example, "expected_names"):
        expected_names = {n.lower() for n in (example.expected_names or [])}
    if expected_names:
        found = {item.get("name", "").lower() for item in items}
        overlap = len(expected_names & found) / max(len(expected_names), 1)
        score += 0.3 * overlap
    else:
        score += 0.15  # partial credit when no expected names

    # Valid confidence range
    valid_conf = sum(
        1 for item in items
        if isinstance(item.get("confidence"), (int, float))
        and 0 <= item["confidence"] <= 1
    )
    score += 0.2 * (valid_conf / max(len(items), 1))

    # Specific domains (not all GENERAL)
    domains = [item.get("domain", "general") for item in items]
    non_general = sum(1 for d in domains if d != "general")
    score += 0.2 * min(1.0, non_general / max(len(items), 1))

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Research metric
# ---------------------------------------------------------------------------


def research_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score research output: non-empty (0.3), field completeness (0.5),
    non-unknown funding (0.2)."""
    output = getattr(prediction, "profiles_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.3  # non-empty

    # Field completeness
    key_fields = [
        "company_name", "r_and_d_approach", "culture", "ml_use_cases",
        "funding_stage", "hiring_signals",
    ]
    total_complete = 0
    for item in items:
        filled = sum(1 for f in key_fields if item.get(f))
        total_complete += filled / len(key_fields)
    score += 0.5 * (total_complete / max(len(items), 1))

    # Non-unknown funding stages
    non_unknown = sum(
        1 for item in items if item.get("funding_stage", "unknown") != "unknown"
    )
    score += 0.2 * (non_unknown / max(len(items), 1))

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Skills metric
# ---------------------------------------------------------------------------


def skills_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score skills output: non-empty (0.3), field completeness (0.5),
    varied alignment scores (0.2)."""
    output = getattr(prediction, "analyses_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.3  # non-empty

    # Field completeness
    key_fields = [
        "company_name", "tools_used", "ml_frameworks", "cloud_platform",
        "skills_to_learn", "alignment_score", "gap_analysis",
    ]
    total_complete = 0
    for item in items:
        filled = sum(1 for f in key_fields if item.get(f))
        total_complete += filled / len(key_fields)
    score += 0.5 * (total_complete / max(len(items), 1))

    # Varied alignment scores
    scores = []
    for item in items:
        s = item.get("alignment_score")
        if isinstance(s, (int, float)) and 0 <= s <= 1:
            scores.append(s)
    if len(scores) >= 2:
        variance = max(scores) - min(scores)
        score += 0.2 * min(1.0, variance / 0.5)
    elif scores:
        score += 0.1

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Contact metric
# ---------------------------------------------------------------------------


def contact_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score contact output: non-empty (0.3), name+title+email/linkedin completeness (0.7)."""
    output = getattr(prediction, "contacts_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.3  # non-empty

    total_completeness = 0
    for item in items:
        has_name = 1 if item.get("name") else 0
        has_title = 1 if item.get("title") else 0
        has_contact_method = 1 if (item.get("email") or item.get("linkedin_url")) else 0
        total_completeness += (has_name + has_title + has_contact_method) / 3
    score += 0.7 * (total_completeness / max(len(items), 1))

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Resume metric
# ---------------------------------------------------------------------------


def resume_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score resume output: non-empty (0.3), summary+emphasis+bullets completeness (0.7)."""
    output = getattr(prediction, "resumes_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.3  # non-empty

    total_completeness = 0
    for item in items:
        has_summary = 1 if len(item.get("tailored_summary", "")) > 20 else 0
        has_emphasis = 1 if item.get("emphasis_areas") else 0
        has_bullets = 1 if item.get("tailored_bullets") else 0
        total_completeness += (has_summary + has_emphasis + has_bullets) / 3
    score += 0.7 * (total_completeness / max(len(items), 1))

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Outreach metric
# ---------------------------------------------------------------------------

FORBIDDEN_WORDS = {"urgent", "act now", "limited time", "guaranteed"}


def outreach_metric(example: Any, prediction: Any, trace: Any = None) -> float:
    """Score outreach output: non-empty (0.2), subject<80+body 50-350 words
    +no forbidden words+personalization (0.8)."""
    output = getattr(prediction, "drafts_json", "")
    items = _safe_parse(output)

    if not items:
        return 0.0

    score = 0.2  # non-empty

    total_quality = 0
    for item in items:
        sub_score = 0.0
        subject = item.get("subject", "")
        body = item.get("body", "")
        word_count = len(body.split())

        # Subject < 80 chars
        if subject and len(subject) < 80:
            sub_score += 0.25

        # Body 50-350 words
        if 50 <= word_count <= 350:
            sub_score += 0.25

        # No forbidden words
        body_lower = body.lower()
        has_forbidden = any(fw in body_lower for fw in FORBIDDEN_WORDS)
        if not has_forbidden:
            sub_score += 0.25

        # Personalization
        if item.get("personalization_notes") or item.get("contact_name"):
            sub_score += 0.25

        total_quality += sub_score

    score += 0.8 * (total_quality / max(len(items), 1))

    return min(1.0, score)
