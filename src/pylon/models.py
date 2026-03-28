"""
All Pydantic models for the CastNet platform.
Single source of truth — no scattered model files.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IntentPriority(int, Enum):
    """7-level priority for intent classification."""
    EMERGENCY = 1
    DISCOVER = 2
    RESEARCH = 3
    SKILLS = 4
    CONTACT = 5
    OUTREACH = 6
    REVIEW = 7


class IndustryDomain(str, Enum):
    """Industry domains for company discovery."""
    SPORTS_TECH = "sports_tech"
    FINTECH = "fintech"
    HEALTH_TECH = "health_tech"
    EDTECH = "edtech"
    GAMING = "gaming"
    ECOMMERCE = "ecommerce"
    CLIMATE_TECH = "climate_tech"
    MEDIA = "media"
    GENERAL = "general"


class ContractStatus(str, Enum):
    """Status codes for RouterContract accountability."""
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCKED = "BLOCKED"
    EXECUTED = "EXECUTED"
    ESCALATE = "ESCALATE"
    SWARM_COMPLETE = "SWARM_COMPLETE"


class OutreachStatus(str, Enum):
    """Status tracking for outreach drafts."""
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"


class FundingStage(str, Enum):
    """Company funding stage."""
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    PUBLIC = "public"
    BOOTSTRAPPED = "bootstrapped"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Pipeline Data Models
# ---------------------------------------------------------------------------


class CompanyCandidate(BaseModel):
    """A company identified by DiscoveryAgent."""
    name: str
    domain: IndustryDomain = IndustryDomain.GENERAL
    relevance_reason: str
    website: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class CompanyProfile(BaseModel):
    """Deep research on a company by ResearchAgent."""
    company_name: str
    r_and_d_approach: str = ""
    engineering_blog: str = ""
    notable_clients: list[str] = Field(default_factory=list)
    culture: str = ""
    ml_use_cases: list[str] = Field(default_factory=list)
    funding_stage: FundingStage = FundingStage.UNKNOWN
    hiring_signals: list[str] = Field(default_factory=list)
    headquarters: str = ""
    employee_count: str = ""


class SkillsAnalysis(BaseModel):
    """Tech stack + skill gap analysis by SkillsAgent."""
    company_name: str
    tools_used: list[str] = Field(default_factory=list)
    ml_frameworks: list[str] = Field(default_factory=list)
    cloud_platform: str = ""
    skills_to_learn: list[str] = Field(default_factory=list)
    alignment_score: float = Field(ge=0.0, le=1.0, default=0.0)
    gap_analysis: str = ""


class ContactInfo(BaseModel):
    """Contact information found by ContactAgent."""
    company_name: str
    name: str
    title: str = ""
    email: str = ""
    linkedin_url: str = ""
    notes: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ResumeVersion(BaseModel):
    """Tailored resume version by ResumeAgent."""
    company_name: str
    tailored_summary: str = ""
    emphasis_areas: list[str] = Field(default_factory=list)
    highlighted_projects: list[str] = Field(default_factory=list)
    tailored_bullets: list[str] = Field(default_factory=list)

    @field_validator("highlighted_projects", "tailored_bullets", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return [str(v)] if v else []
        return [
            item if isinstance(item, str)
            else " — ".join(str(val) for val in item.values()) if isinstance(item, dict)
            else str(item)
            for item in v
        ]


class ToolSuggestion(BaseModel):
    """A buildable tool/product suggestion for impressing a company."""
    company_name: str
    tool_name: str
    description: str = ""
    why_impressive: str = ""
    estimated_revenue_impact: str = ""


class OutreachDraft(BaseModel):
    """Personalized cold email by OutreachAgent."""
    company_name: str
    contact_name: str = ""
    subject: str = ""
    body: str = ""
    personalization_notes: str = ""
    template_used: str = ""
    gmail_draft_id: str = ""
    status: OutreachStatus = OutreachStatus.DRAFT

    @field_validator("personalization_notes", mode="before")
    @classmethod
    def _coerce_notes(cls, v: Any) -> str:
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        return str(v) if v else ""


# ---------------------------------------------------------------------------
# Pipeline Context
# ---------------------------------------------------------------------------


class PipelineContext(BaseModel):
    """Carries all intermediate data for a single search pipeline run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    intent: Optional[Intent] = None
    candidates: list[CompanyCandidate] = Field(default_factory=list)
    profiles: list[CompanyProfile] = Field(default_factory=list)
    skills: list[SkillsAnalysis] = Field(default_factory=list)
    tools: list[ToolSuggestion] = Field(default_factory=list)
    contacts: list[ContactInfo] = Field(default_factory=list)
    resumes: list[ResumeVersion] = Field(default_factory=list)
    drafts: list[OutreachDraft] = Field(default_factory=list)
    excel_path: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def new(cls, query: str) -> PipelineContext:
        return cls(query=query)


# ---------------------------------------------------------------------------
# Router & Orchestration
# ---------------------------------------------------------------------------


class RouterContract(BaseModel):
    """Universal output contract for every agent interaction."""
    status: ContractStatus
    confidence: float = Field(ge=0.0, le=100.0, default=50.0)
    critical_issues: int = 0
    blocking: bool = False
    kb_update_notes: str = ""
    evidence: str = ""

    def is_approvable(self) -> bool:
        return self.status == ContractStatus.APPROVED and self.confidence >= 60.0

    def is_executable(self) -> bool:
        return self.status == ContractStatus.EXECUTED and not self.blocking


class Intent(BaseModel):
    """Classified user intent with priority routing."""
    priority: IntentPriority
    domain: IndustryDomain = IndustryDomain.GENERAL
    raw_query: str = ""
    swarm_worthy: bool = False


# ---------------------------------------------------------------------------
# Search & Session
# ---------------------------------------------------------------------------


class SearchConfig(BaseModel):
    """Configuration for a search pipeline run."""
    max_companies: int = 30
    max_outreach_per_day: int = 10
    include_skills_analysis: bool = True
    include_contact_search: bool = True
    include_resume_tailoring: bool = True
    include_outreach: bool = True


class SessionStats(BaseModel):
    """Telemetry for a pipeline session."""
    run_id: str = ""
    total_companies: int = 0
    profiles_researched: int = 0
    contacts_found: int = 0
    drafts_generated: int = 0
    total_tokens_used: int = 0
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------


class SwarmChannel(BaseModel):
    """A parallel research channel in the swarm workflow."""
    channel_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    company_name: str
    task_description: str = ""
    agent_type: str = "research"


class SwarmResult(BaseModel):
    """Result from a single swarm channel."""
    channel_id: str
    company_name: str
    findings: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    cross_channel_insights: list[str] = Field(default_factory=list)
