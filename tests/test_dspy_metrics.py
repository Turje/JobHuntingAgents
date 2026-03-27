"""Tests for src/pylon/dspy_/metrics.py — verify metrics return [0,1]."""

import json
from types import SimpleNamespace

import pytest

from pylon.dspy_.metrics import (
    contact_metric,
    discovery_metric,
    outreach_metric,
    research_metric,
    resume_metric,
    skills_metric,
)


def _pred(**kwargs):
    """Create a simple prediction-like namespace."""
    return SimpleNamespace(**kwargs)


def _example(**kwargs):
    """Create a simple example-like namespace."""
    return SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class TestDiscoveryMetric:
    def test_empty_output_returns_zero(self):
        score = discovery_metric(_example(), _pred(companies_json=""))
        assert score == 0.0

    def test_invalid_json_returns_zero(self):
        score = discovery_metric(_example(), _pred(companies_json="not json"))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        data = json.dumps([
            {"name": "Acme", "domain": "fintech", "confidence": 0.9},
            {"name": "Beta", "domain": "sports_tech", "confidence": 0.8},
        ])
        score = discovery_metric(_example(), _pred(companies_json=data))
        assert 0.0 < score <= 1.0

    def test_with_expected_names(self):
        data = json.dumps([
            {"name": "Acme", "domain": "fintech", "confidence": 0.9},
        ])
        score = discovery_metric(
            _example(expected_names=["Acme", "Beta"]),
            _pred(companies_json=data),
        )
        assert 0.0 < score <= 1.0


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


class TestResearchMetric:
    def test_empty_output_returns_zero(self):
        score = research_metric(_example(), _pred(profiles_json=""))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        data = json.dumps([{
            "company_name": "Acme",
            "r_and_d_approach": "ML-first",
            "culture": "Fast",
            "ml_use_cases": ["fraud"],
            "funding_stage": "series_a",
            "hiring_signals": ["growing"],
        }])
        score = research_metric(_example(), _pred(profiles_json=data))
        assert 0.5 < score <= 1.0

    def test_partial_output_returns_middle(self):
        data = json.dumps([{"company_name": "Acme"}])
        score = research_metric(_example(), _pred(profiles_json=data))
        assert 0.3 <= score < 0.8


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSkillsMetric:
    def test_empty_output_returns_zero(self):
        score = skills_metric(_example(), _pred(analyses_json=""))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        data = json.dumps([
            {"company_name": "Acme", "tools_used": ["Python"], "ml_frameworks": ["PyTorch"],
             "cloud_platform": "AWS", "skills_to_learn": ["Spark"],
             "alignment_score": 0.9, "gap_analysis": "Need Spark"},
            {"company_name": "Beta", "tools_used": ["Java"], "ml_frameworks": ["TF"],
             "cloud_platform": "GCP", "skills_to_learn": ["Go"],
             "alignment_score": 0.4, "gap_analysis": "Need Go"},
        ])
        score = skills_metric(_example(), _pred(analyses_json=data))
        assert 0.5 < score <= 1.0


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------


class TestContactMetric:
    def test_empty_output_returns_zero(self):
        score = contact_metric(_example(), _pred(contacts_json=""))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        data = json.dumps([
            {"company_name": "Acme", "name": "John", "title": "CTO",
             "email": "j@acme.com", "linkedin_url": "https://linkedin.com/in/john"},
        ])
        score = contact_metric(_example(), _pred(contacts_json=data))
        assert 0.8 < score <= 1.0

    def test_partial_output(self):
        data = json.dumps([{"company_name": "Acme", "name": "John"}])
        score = contact_metric(_example(), _pred(contacts_json=data))
        assert 0.3 < score < 0.9


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


class TestResumeMetric:
    def test_empty_output_returns_zero(self):
        score = resume_metric(_example(), _pred(resumes_json=""))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        data = json.dumps([{
            "company_name": "Acme",
            "tailored_summary": "Experienced ML engineer with deep expertise in fraud detection",
            "emphasis_areas": ["fraud", "ML"],
            "tailored_bullets": ["Built fraud models", "Scaled ML pipeline"],
        }])
        score = resume_metric(_example(), _pred(resumes_json=data))
        assert 0.8 < score <= 1.0


# ---------------------------------------------------------------------------
# Outreach
# ---------------------------------------------------------------------------


class TestOutreachMetric:
    def test_empty_output_returns_zero(self):
        score = outreach_metric(_example(), _pred(drafts_json=""))
        assert score == 0.0

    def test_good_output_returns_positive(self):
        body = " ".join(["word"] * 150)
        data = json.dumps([{
            "company_name": "Acme",
            "contact_name": "John",
            "subject": "ML opportunity at Acme",
            "body": body,
            "personalization_notes": "Mentioned fraud detection work",
        }])
        score = outreach_metric(_example(), _pred(drafts_json=data))
        assert 0.8 < score <= 1.0

    def test_forbidden_words_reduce_score(self):
        body = "This is urgent! Act now for a guaranteed opportunity. " + " ".join(["word"] * 100)
        data = json.dumps([{
            "company_name": "Acme",
            "contact_name": "John",
            "subject": "ML role",
            "body": body,
            "personalization_notes": "test",
        }])
        score_bad = outreach_metric(_example(), _pred(drafts_json=data))

        clean_body = "I was impressed by your work on fraud detection. " + " ".join(["word"] * 100)
        clean_data = json.dumps([{
            "company_name": "Acme",
            "contact_name": "John",
            "subject": "ML role",
            "body": clean_body,
            "personalization_notes": "test",
        }])
        score_good = outreach_metric(_example(), _pred(drafts_json=clean_data))
        assert score_good > score_bad
