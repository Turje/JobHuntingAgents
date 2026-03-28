"""Tests for src/pylon/models.py — all Pydantic models."""

import uuid

import pytest
from pydantic import ValidationError

from pylon.models import (
    CompanyCandidate,
    CompanyProfile,
    ContactInfo,
    ContractStatus,
    FundingStage,
    IndustryDomain,
    Intent,
    IntentPriority,
    OutreachDraft,
    OutreachStatus,
    PipelineContext,
    ResumeVersion,
    RouterContract,
    SearchConfig,
    SessionStats,
    SkillsAnalysis,
    SwarmChannel,
    SwarmResult,
    ToolSuggestion,
)


# ---------------------------------------------------------------------------
# CompanyCandidate
# ---------------------------------------------------------------------------

class TestCompanyCandidate:
    def test_create_minimal(self):
        c = CompanyCandidate(name="StatsBomb", relevance_reason="Football analytics")
        assert c.name == "StatsBomb"
        assert c.domain == IndustryDomain.GENERAL
        assert c.confidence == 0.5

    def test_create_full(self):
        c = CompanyCandidate(
            name="Opta",
            domain=IndustryDomain.SPORTS_TECH,
            relevance_reason="Premier League data",
            website="https://opta.com",
            confidence=0.9,
        )
        assert c.domain == IndustryDomain.SPORTS_TECH
        assert c.confidence == 0.9

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            CompanyCandidate(name="X", relevance_reason="Y", confidence=1.5)
        with pytest.raises(ValidationError):
            CompanyCandidate(name="X", relevance_reason="Y", confidence=-0.1)


# ---------------------------------------------------------------------------
# CompanyProfile
# ---------------------------------------------------------------------------

class TestCompanyProfile:
    def test_defaults(self):
        p = CompanyProfile(company_name="TestCo")
        assert p.notable_clients == []
        assert p.funding_stage == FundingStage.UNKNOWN

    def test_full_profile(self):
        p = CompanyProfile(
            company_name="DataCo",
            r_and_d_approach="ML-first",
            ml_use_cases=["recommendation", "NLP"],
            funding_stage=FundingStage.SERIES_B,
            hiring_signals=["Posted 3 ML roles"],
        )
        assert len(p.ml_use_cases) == 2
        assert p.funding_stage == FundingStage.SERIES_B


# ---------------------------------------------------------------------------
# SkillsAnalysis
# ---------------------------------------------------------------------------

class TestSkillsAnalysis:
    def test_alignment_bounds(self):
        s = SkillsAnalysis(company_name="X", alignment_score=0.85)
        assert s.alignment_score == 0.85

        with pytest.raises(ValidationError):
            SkillsAnalysis(company_name="X", alignment_score=2.0)


# ---------------------------------------------------------------------------
# ContactInfo
# ---------------------------------------------------------------------------

class TestContactInfo:
    def test_create(self):
        c = ContactInfo(company_name="TestCo", name="Jane Doe", title="CTO")
        assert c.title == "CTO"
        assert c.confidence == 0.5


# ---------------------------------------------------------------------------
# ResumeVersion
# ---------------------------------------------------------------------------

class TestResumeVersion:
    def test_create(self):
        r = ResumeVersion(
            company_name="ML Corp",
            tailored_summary="ML engineer focused on NLP",
            emphasis_areas=["NLP", "PyTorch"],
        )
        assert len(r.emphasis_areas) == 2


# ---------------------------------------------------------------------------
# OutreachDraft
# ---------------------------------------------------------------------------

class TestOutreachDraft:
    def test_defaults(self):
        d = OutreachDraft(company_name="TestCo")
        assert d.status == OutreachStatus.DRAFT

    def test_status_transitions(self):
        d = OutreachDraft(company_name="TestCo", status=OutreachStatus.SENT)
        assert d.status == OutreachStatus.SENT


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------

class TestToolSuggestion:
    def test_create(self):
        t = ToolSuggestion(
            company_name="Acme",
            tool_name="Widget API",
            description="Builds cool widgets",
            why_impressive="Solves their main pain point",
            estimated_revenue_impact="$100K/year",
        )
        assert t.company_name == "Acme"
        assert t.tool_name == "Widget API"

    def test_defaults(self):
        t = ToolSuggestion(company_name="Acme", tool_name="Test")
        assert t.description == ""
        assert t.why_impressive == ""
        assert t.estimated_revenue_impact == ""


class TestPipelineContext:
    def test_new_creates_uuid(self):
        ctx = PipelineContext.new("find football companies")
        assert ctx.query == "find football companies"
        uuid.UUID(ctx.run_id)  # validates it's a real UUID

    def test_empty_lists(self):
        ctx = PipelineContext.new("test")
        assert ctx.candidates == []
        assert ctx.profiles == []
        assert ctx.drafts == []

    def test_tools_field(self):
        ctx = PipelineContext.new("test")
        assert ctx.tools == []
        ctx.tools.append(ToolSuggestion(company_name="A", tool_name="Widget"))
        assert len(ctx.tools) == 1

    def test_mutable_lists(self):
        ctx = PipelineContext.new("test")
        ctx.candidates.append(
            CompanyCandidate(name="A", relevance_reason="test")
        )
        assert len(ctx.candidates) == 1


# ---------------------------------------------------------------------------
# RouterContract
# ---------------------------------------------------------------------------

class TestRouterContract:
    def test_is_approvable(self):
        rc = RouterContract(status=ContractStatus.APPROVED, confidence=75.0)
        assert rc.is_approvable() is True

    def test_not_approvable_low_confidence(self):
        rc = RouterContract(status=ContractStatus.APPROVED, confidence=50.0)
        assert rc.is_approvable() is False

    def test_not_approvable_wrong_status(self):
        rc = RouterContract(status=ContractStatus.PLANNED, confidence=90.0)
        assert rc.is_approvable() is False

    def test_is_executable(self):
        rc = RouterContract(status=ContractStatus.EXECUTED, blocking=False)
        assert rc.is_executable() is True

    def test_not_executable_blocking(self):
        rc = RouterContract(status=ContractStatus.EXECUTED, blocking=True)
        assert rc.is_executable() is False


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

class TestIntent:
    def test_priority_ordering(self):
        assert IntentPriority.EMERGENCY < IntentPriority.DISCOVER
        assert IntentPriority.DISCOVER < IntentPriority.REVIEW

    def test_create(self):
        i = Intent(
            priority=IntentPriority.DISCOVER,
            domain=IndustryDomain.SPORTS_TECH,
            raw_query="find football ML companies",
            swarm_worthy=True,
        )
        assert i.swarm_worthy is True


# ---------------------------------------------------------------------------
# SearchConfig & SessionStats
# ---------------------------------------------------------------------------

class TestSearchConfig:
    def test_defaults(self):
        sc = SearchConfig()
        assert sc.max_companies == 15
        assert sc.include_outreach is True


class TestSessionStats:
    def test_defaults(self):
        ss = SessionStats()
        assert ss.total_companies == 0


# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------

class TestSwarmChannel:
    def test_auto_id(self):
        ch = SwarmChannel(company_name="TestCo")
        assert len(ch.channel_id) == 8


class TestSwarmResult:
    def test_create(self):
        sr = SwarmResult(channel_id="abc", company_name="TestCo", confidence=0.7)
        assert sr.confidence == 0.7
