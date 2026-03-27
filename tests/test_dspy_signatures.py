"""Tests for src/pylon/dspy_/signatures.py — verify signature field definitions."""

import pytest
import dspy

from pylon.dspy_.signatures import (
    AnalyzeSkills,
    CritiqueOutreach,
    CritiqueSearch,
    DiscoverCompanies,
    DraftOutreach,
    FindContacts,
    PlanSearch,
    ResearchCompanies,
    TailorResumes,
)


class TestDiscoverCompaniesSignature:
    def test_input_fields(self):
        fields = DiscoverCompanies.input_fields
        assert "query" in fields
        assert "domain_hint" in fields
        assert "web_context" in fields
        assert "max_companies" in fields

    def test_output_fields(self):
        fields = DiscoverCompanies.output_fields
        assert "companies_json" in fields


class TestResearchCompaniesSignature:
    def test_input_fields(self):
        fields = ResearchCompanies.input_fields
        assert "query" in fields
        assert "companies_json" in fields
        assert "web_context" in fields

    def test_output_fields(self):
        fields = ResearchCompanies.output_fields
        assert "profiles_json" in fields


class TestAnalyzeSkillsSignature:
    def test_input_fields(self):
        fields = AnalyzeSkills.input_fields
        assert "query" in fields
        assert "profiles_json" in fields
        assert "web_context" in fields

    def test_output_fields(self):
        fields = AnalyzeSkills.output_fields
        assert "analyses_json" in fields


class TestFindContactsSignature:
    def test_input_fields(self):
        fields = FindContacts.input_fields
        assert "query" in fields
        assert "companies_json" in fields
        assert "web_context" in fields

    def test_output_fields(self):
        fields = FindContacts.output_fields
        assert "contacts_json" in fields


class TestTailorResumesSignature:
    def test_input_fields(self):
        fields = TailorResumes.input_fields
        assert "query" in fields
        assert "companies_json" in fields

    def test_output_fields(self):
        fields = TailorResumes.output_fields
        assert "resumes_json" in fields


class TestDraftOutreachSignature:
    def test_input_fields(self):
        fields = DraftOutreach.input_fields
        assert "query" in fields
        assert "contacts_json" in fields

    def test_output_fields(self):
        fields = DraftOutreach.output_fields
        assert "drafts_json" in fields


class TestPlanSearchSignature:
    def test_input_fields(self):
        fields = PlanSearch.input_fields
        assert "task" in fields
        assert "feedback" in fields

    def test_output_fields(self):
        fields = PlanSearch.output_fields
        assert "plan" in fields


class TestCritiqueSearchSignature:
    def test_input_fields(self):
        fields = CritiqueSearch.input_fields
        assert "task" in fields
        assert "plan" in fields

    def test_output_fields(self):
        fields = CritiqueSearch.output_fields
        assert "verdict" in fields
        assert "confidence" in fields


class TestCritiqueOutreachSignature:
    def test_input_fields(self):
        fields = CritiqueOutreach.input_fields
        assert "context" in fields
        assert "draft" in fields

    def test_output_fields(self):
        fields = CritiqueOutreach.output_fields
        assert "verdict" in fields
        assert "confidence" in fields
