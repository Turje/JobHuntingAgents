"""
DSPy Signatures for all CastNet agents.
Each signature has typed I/O; docstrings become the optimizable instructions.
"""

from __future__ import annotations

import dspy


# ---------------------------------------------------------------------------
# Pipeline Agent Signatures
# ---------------------------------------------------------------------------


class DiscoverCompanies(dspy.Signature):
    """Given a job seeker's query and optional industry focus, discover companies
    that match their interests. Return a JSON array of company candidates with
    name, domain, relevance_reason, website, and confidence (0-1)."""

    query: str = dspy.InputField(desc="The job seeker's free-text search query")
    domain_hint: str = dspy.InputField(
        desc="Optional industry focus (e.g. sports_tech, fintech)", default=""
    )
    web_context: str = dspy.InputField(
        desc="Optional web search results for grounding", default=""
    )
    max_companies: int = dspy.InputField(
        desc="Maximum number of companies to return", default=30
    )
    companies_json: str = dspy.OutputField(
        desc="JSON array of CompanyCandidate objects with name, domain, relevance_reason, website, confidence"
    )


class ResearchCompanies(dspy.Signature):
    """Research the given companies in depth for a job seeker. For each company,
    produce a detailed profile covering R&D approach, engineering blog, notable
    clients, culture, ML use cases, funding stage, hiring signals, headquarters,
    and employee count. Return a JSON array of company profiles."""

    query: str = dspy.InputField(desc="The job seeker's original search query")
    companies_json: str = dspy.InputField(
        desc="JSON array of company candidates to research"
    )
    web_context: str = dspy.InputField(
        desc="Optional web search results about these companies", default=""
    )
    profiles_json: str = dspy.OutputField(
        desc="JSON array of CompanyProfile objects with detailed research"
    )


class AnalyzeSkills(dspy.Signature):
    """Analyze tech stacks and skill gaps for the given company profiles relative
    to the job seeker's background. For each company, identify tools used, ML
    frameworks, cloud platform, skills to learn, alignment score (0-1), and
    gap analysis. Return a JSON array."""

    query: str = dspy.InputField(desc="The job seeker's search query")
    profiles_json: str = dspy.InputField(
        desc="JSON array of company profiles to analyze"
    )
    web_context: str = dspy.InputField(
        desc="Optional web search results about job requirements", default=""
    )
    analyses_json: str = dspy.OutputField(
        desc="JSON array of SkillsAnalysis objects"
    )


class SuggestTools(dspy.Signature):
    """Suggest buildable tools, products, or demos for each company that the job
    seeker could create to impress hiring managers. Use the company's tech stack,
    ML use cases, culture, and hiring signals. Return a JSON array with
    tool_name, description, why_impressive, estimated_revenue_impact per company."""

    query: str = dspy.InputField(desc="The job seeker's search query")
    companies_json: str = dspy.InputField(
        desc="JSON array of companies with profiles and skills data"
    )
    web_context: str = dspy.InputField(
        desc="Optional web data about company engineering challenges", default=""
    )
    suggestions_json: str = dspy.OutputField(
        desc="JSON array of ToolSuggestion objects with company_name, tool_name, description, why_impressive, estimated_revenue_impact"
    )


class FindContacts(dspy.Signature):
    """Find decision-makers and hiring managers at the given companies
    relevant to the job seeker's query. Return a JSON array of contacts with
    company_name, name, title, email, linkedin_url, notes, confidence."""

    query: str = dspy.InputField(desc="The job seeker's search context")
    companies_json: str = dspy.InputField(
        desc="JSON array of companies to find contacts for"
    )
    web_context: str = dspy.InputField(
        desc="Optional web data about decision-makers", default=""
    )
    contacts_json: str = dspy.OutputField(
        desc="JSON array of ContactInfo objects"
    )


class TailorResumes(dspy.Signature):
    """Tailor resume content for the job seeker for each target company.
    Use company profiles and skills analysis to produce a tailored summary,
    emphasis areas, highlighted projects, and tailored bullets.
    Return a JSON array of resume versions."""

    query: str = dspy.InputField(desc="The job seeker's search query")
    companies_json: str = dspy.InputField(
        desc="JSON array of companies with profiles, skills, and relevance data"
    )
    resumes_json: str = dspy.OutputField(
        desc="JSON array of ResumeVersion objects"
    )


class DraftOutreach(dspy.Signature):
    """Draft personalized cold outreach emails for each contact. Emails must be
    under 300 words, avoid forbidden words (urgent, act now, guaranteed),
    include a personalized opening, and have a clear call-to-action.
    Return a JSON array of outreach drafts."""

    query: str = dspy.InputField(desc="The job seeker's context")
    contacts_json: str = dspy.InputField(
        desc="JSON array of contacts with company context"
    )
    drafts_json: str = dspy.OutputField(
        desc="JSON array of OutreachDraft objects"
    )


# ---------------------------------------------------------------------------
# Actor-Critic Signatures
# ---------------------------------------------------------------------------


class PlanSearch(dspy.Signature):
    """Create a search strategy plan for job hunting. Identify target industries,
    company types, geographic focus, key search terms, and expected company count."""

    task: str = dspy.InputField(desc="The user's job hunting task/query")
    feedback: str = dspy.InputField(
        desc="Previous critic feedback to address", default=""
    )
    plan: str = dspy.OutputField(desc="Structured search strategy plan")


class CritiqueSearch(dspy.Signature):
    """Review a search plan for completeness and quality. Check coverage of
    user interests, appropriate industries, reasonable company count (up to 30),
    and specific search terms. Return APPROVED or REQUEST_CHANGES with feedback."""

    task: str = dspy.InputField(desc="The original search task")
    plan: str = dspy.InputField(desc="The search plan to review")
    verdict: str = dspy.OutputField(
        desc="APPROVED or REQUEST_CHANGES with specific feedback"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score 0-100 for plan quality"
    )


class CritiqueOutreach(dspy.Signature):
    """Review a cold outreach email draft for quality. Check personalization,
    subject line (<80 chars), body (<300 words), forbidden words, and CTA.
    Return APPROVED or REQUEST_CHANGES with specific feedback."""

    context: str = dspy.InputField(desc="The outreach task context")
    draft: str = dspy.InputField(desc="The email draft to review")
    verdict: str = dspy.OutputField(
        desc="APPROVED or REQUEST_CHANGES with specific feedback"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score 0-100 for draft quality"
    )
