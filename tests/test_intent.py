"""Tests for src/pylon/intent.py — intent classification."""

from pylon.intent import classify_intent
from pylon.models import IndustryDomain, IntentPriority


class TestClassifyIntent:
    def test_emergency_stop(self):
        intent = classify_intent("stop everything now")
        assert intent.priority == IntentPriority.EMERGENCY

    def test_emergency_cancel(self):
        intent = classify_intent("cancel the pipeline")
        assert intent.priority == IntentPriority.EMERGENCY

    def test_discover_find(self):
        intent = classify_intent("find ML companies in sports")
        assert intent.priority == IntentPriority.DISCOVER
        assert intent.domain == IndustryDomain.SPORTS_TECH

    def test_discover_companies(self):
        intent = classify_intent("I want to discover companies in fintech")
        assert intent.priority == IntentPriority.DISCOVER
        assert intent.domain == IndustryDomain.FINTECH

    def test_research_deep_dive(self):
        intent = classify_intent("deep dive into StatsBomb")
        assert intent.priority == IntentPriority.RESEARCH

    def test_skills_tech_stack(self):
        intent = classify_intent("what tech stack does Opta use")
        assert intent.priority == IntentPriority.SKILLS

    def test_contact_cto(self):
        intent = classify_intent("who is the CTO of DataCo")
        assert intent.priority == IntentPriority.CONTACT

    def test_outreach_draft(self):
        intent = classify_intent("write a cold outreach pitch")
        assert intent.priority == IntentPriority.OUTREACH

    def test_review_status(self):
        intent = classify_intent("show me the progress")
        assert intent.priority == IntentPriority.REVIEW

    def test_review_export(self):
        intent = classify_intent("export results to excel")
        assert intent.priority == IntentPriority.REVIEW


class TestDomainDetection:
    def test_sports_football(self):
        intent = classify_intent("find football analytics companies")
        assert intent.domain == IndustryDomain.SPORTS_TECH

    def test_fintech(self):
        intent = classify_intent("search for fintech startups")
        assert intent.domain == IndustryDomain.FINTECH

    def test_health_tech(self):
        intent = classify_intent("discover healthcare ML companies")
        assert intent.domain == IndustryDomain.HEALTH_TECH

    def test_edtech(self):
        intent = classify_intent("find education technology firms")
        assert intent.domain == IndustryDomain.EDTECH

    def test_gaming(self):
        intent = classify_intent("search for gaming companies")
        assert intent.domain == IndustryDomain.GAMING

    def test_general_no_domain(self):
        intent = classify_intent("find data science companies")
        assert intent.domain == IndustryDomain.GENERAL


class TestSwarmDetection:
    def test_comprehensive_triggers_swarm(self):
        intent = classify_intent("comprehensive search for sports companies")
        assert intent.swarm_worthy is True

    def test_thorough_triggers_swarm(self):
        intent = classify_intent("thorough investigation of ML companies")
        assert intent.swarm_worthy is True

    def test_simple_query_not_swarm(self):
        intent = classify_intent("find football companies")
        assert intent.swarm_worthy is False

    def test_emergency_never_swarm(self):
        intent = classify_intent("comprehensive stop all operations")
        assert intent.swarm_worthy is False


class TestEdgeCases:
    def test_empty_query(self):
        intent = classify_intent("")
        assert intent.priority == IntentPriority.REVIEW

    def test_whitespace_only(self):
        intent = classify_intent("   ")
        assert intent.priority == IntentPriority.REVIEW

    def test_default_to_discover(self):
        intent = classify_intent("I love European football, ML roles please")
        assert intent.priority == IntentPriority.DISCOVER

    def test_raw_query_preserved(self):
        query = "find football companies"
        intent = classify_intent(query)
        assert intent.raw_query == query
