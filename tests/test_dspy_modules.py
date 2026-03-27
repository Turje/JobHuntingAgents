"""Tests for src/pylon/dspy_/modules.py — verify modules with DummyLM."""

import json
from unittest.mock import patch

import dspy
import pytest

from pylon.dspy_.modules import (
    ContactModule,
    CritiqueOutreachModule,
    CritiqueSearchModule,
    DiscoveryModule,
    OutreachModule,
    PlanSearchModule,
    ResearchModule,
    ResumeModule,
    SkillsModule,
)


DUMMY_DISCOVERY = json.dumps([
    {"name": "Acme", "domain": "fintech", "relevance_reason": "Fintech leader",
     "website": "https://acme.com", "confidence": 0.9}
])

DUMMY_PROFILES = json.dumps([
    {"company_name": "Acme", "r_and_d_approach": "ML-first",
     "culture": "Fast-paced", "ml_use_cases": ["fraud"], "funding_stage": "series_a"}
])

DUMMY_SKILLS = json.dumps([
    {"company_name": "Acme", "tools_used": ["Python"], "ml_frameworks": ["PyTorch"],
     "cloud_platform": "AWS", "alignment_score": 0.8, "gap_analysis": "Need Spark"}
])

DUMMY_CONTACTS = json.dumps([
    {"company_name": "Acme", "name": "John Doe", "title": "CTO",
     "email": "john@acme.com", "confidence": 0.9}
])

DUMMY_RESUMES = json.dumps([
    {"company_name": "Acme", "tailored_summary": "ML expert for fintech",
     "emphasis_areas": ["fraud detection"], "tailored_bullets": ["Built models"]}
])

DUMMY_DRAFTS = json.dumps([
    {"company_name": "Acme", "contact_name": "John Doe",
     "subject": "ML role at Acme", "body": "Hi John, " + "word " * 100,
     "personalization_notes": "Fraud detection focus"}
])


def _make_lm(responses):
    """Create a DummyLM that repeats the same response for each call."""
    dummy = dspy.utils.DummyLM(responses)
    dspy.configure(lm=dummy)
    return dummy


class TestDiscoveryModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"companies_json": DUMMY_DISCOVERY, "reasoning": "Found companies"}] * 3)
        module = DiscoveryModule()
        result = module(query="fintech companies", domain_hint="fintech")
        assert hasattr(result, "companies_json")
        parsed = json.loads(result.companies_json)
        assert isinstance(parsed, list)
        assert parsed[0]["name"] == "Acme"


class TestResearchModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"profiles_json": DUMMY_PROFILES, "reasoning": "Researched"}] * 3)
        module = ResearchModule()
        companies = json.dumps([{"name": "Acme", "domain": "fintech"}])
        result = module(query="fintech jobs", companies_json=companies)
        assert hasattr(result, "profiles_json")
        parsed = json.loads(result.profiles_json)
        assert parsed[0]["company_name"] == "Acme"


class TestSkillsModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"analyses_json": DUMMY_SKILLS, "reasoning": "Analyzed"}] * 3)
        module = SkillsModule()
        result = module(query="ML jobs", profiles_json=DUMMY_PROFILES)
        assert hasattr(result, "analyses_json")
        parsed = json.loads(result.analyses_json)
        assert parsed[0]["alignment_score"] == 0.8


class TestContactModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"contacts_json": DUMMY_CONTACTS, "reasoning": "Found contacts"}] * 3)
        module = ContactModule()
        companies = json.dumps([{"company_name": "Acme"}])
        result = module(query="fintech", companies_json=companies)
        assert hasattr(result, "contacts_json")
        parsed = json.loads(result.contacts_json)
        assert parsed[0]["name"] == "John Doe"


class TestResumeModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"resumes_json": DUMMY_RESUMES, "reasoning": "Tailored"}] * 3)
        module = ResumeModule()
        companies = json.dumps([{"company_name": "Acme", "relevance": "Fintech"}])
        result = module(query="fintech jobs", companies_json=companies)
        assert hasattr(result, "resumes_json")
        parsed = json.loads(result.resumes_json)
        assert parsed[0]["company_name"] == "Acme"


class TestOutreachModule:
    def test_forward_returns_prediction(self):
        _make_lm([{"drafts_json": DUMMY_DRAFTS, "reasoning": "Drafted"}] * 3)
        module = OutreachModule()
        result = module(query="fintech", contacts_json=DUMMY_CONTACTS)
        assert hasattr(result, "drafts_json")
        parsed = json.loads(result.drafts_json)
        assert parsed[0]["contact_name"] == "John Doe"


class TestPlanSearchModule:
    def test_forward_returns_plan(self):
        _make_lm([{"plan": "Target fintech companies in NYC", "reasoning": "Planned"}] * 3)
        module = PlanSearchModule()
        result = module(task="find fintech companies")
        assert hasattr(result, "plan")
        assert len(result.plan) > 0


class TestCritiqueSearchModule:
    def test_forward_returns_verdict(self):
        _make_lm([{"verdict": "APPROVED", "confidence": 80.0, "reasoning": "Good plan"}] * 3)
        module = CritiqueSearchModule()
        result = module(task="find fintech", plan="Target fintech in NYC")
        assert hasattr(result, "verdict")
        assert "APPROVED" in result.verdict.upper()


class TestCritiqueOutreachModule:
    def test_forward_returns_verdict(self):
        _make_lm([{"verdict": "APPROVED", "confidence": 85.0, "reasoning": "Good email"}] * 3)
        module = CritiqueOutreachModule()
        result = module(context="fintech outreach", draft="Hi John...")
        assert hasattr(result, "verdict")
