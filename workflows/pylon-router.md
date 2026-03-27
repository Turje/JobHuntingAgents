# JobHuntingAgents Router

The Router is the central orchestrator of JobHuntingAgents. It receives every user query, classifies intent, dispatches to the appropriate workflow or agent, collects results, and feeds knowledge back into stable-anchor memory.

## Purpose

- **Intent classification**: Parse the user's natural language query into a structured `Intent` with priority, domain, and swarm eligibility.
- **Dispatch**: Route the classified intent to the correct workflow (AC Planning, Swarm, or direct agent call).
- **Result collection**: Receive `RouterContract` responses from every agent interaction and decide what happens next.
- **Knowledge accumulation**: After completed loops, persist learned patterns and progress to `memory/`.

## 7-Priority Routing Table

Every query is classified into one of seven priority levels. Priority determines dispatch order and which agents are activated.

| Priority | Name | Value | Description | Dispatch Target |
|----------|------|-------|-------------|-----------------|
| 1 | `EMERGENCY` | 1 | Urgent time-sensitive requests (deadline, expiring opportunity) | Hot path: immediate pipeline with shortened AC budget |
| 2 | `DISCOVER` | 2 | Find new companies in a domain | AC Planning -> DiscoveryAgent -> pipeline |
| 3 | `RESEARCH` | 3 | Deep-dive on known companies | AC Planning -> ResearchAgent (or Swarm if swarm_worthy) |
| 4 | `SKILLS` | 4 | Tech stack and skill gap analysis | SkillsAgent (may skip AC if target company is already profiled) |
| 5 | `CONTACT` | 5 | Find hiring managers and contacts | ContactAgent |
| 6 | `OUTREACH` | 6 | Draft and review cold emails | AC Outreach -> OutreachDrafter/OutreachCritic |
| 7 | `REVIEW` | 7 | Review existing drafts, pipeline results, or session history | Read-only: query SessionStore, no agent dispatch |

Priority levels are defined by the `IntentPriority` enum in `src/pylon/models.py`.

## Intent Classification

The Router produces an `Intent` object from the raw query:

```python
class Intent(BaseModel):
    priority: IntentPriority        # One of the 7 levels
    domain: IndustryDomain          # sports_tech, fintech, health_tech, etc.
    raw_query: str                  # Original user input, preserved verbatim
    swarm_worthy: bool              # True if broad multi-company research detected
```

Classification considers:
- **Explicit keywords** for priority (e.g., "urgent", "deadline" -> EMERGENCY; "find companies" -> DISCOVER).
- **Domain signals** matched against the `IndustryDomain` enum values.
- **Swarm indicators** (see `workflows/swarm.md`) that set `swarm_worthy = True`.

## Hot Path vs Cold Path

### Hot Path -- `pipeline.run()`

The hot path is the full sequential pipeline triggered by DISCOVER or RESEARCH intents. It runs:

```
Intent -> AC Planning (max 3 cycles)
  -> DiscoveryAgent -> ResearchAgent -> SkillsAgent -> ContactAgent
  -> ResumeAgent -> AC Outreach (max 3 cycles per draft)
  -> Excel export -> [Gmail draft creation]
```

This is the default path for most queries. It creates a `PipelineContext`, runs through all stages, and writes results to `SessionStore`.

EMERGENCY priority uses the same hot path but with a compressed flow: the AC cycle budget may be reduced and low-priority stages (resume tailoring, outreach) can be skipped to deliver results faster.

### Cold Path -- Intent-Based Dispatch

For narrower intents (SKILLS, CONTACT, OUTREACH, REVIEW), the Router dispatches directly to the relevant agent or subsystem without running the full pipeline.

| Intent | Cold Path Action |
|--------|-----------------|
| SKILLS | Load existing `CompanyProfile` from store, run SkillsAgent, return `SkillsAnalysis`. |
| CONTACT | Load existing profile, run ContactAgent, return `ContactInfo` list. |
| OUTREACH | Load profile + contacts + skills, enter AC Outreach loop. |
| REVIEW | Query `SessionStore` for past runs, return formatted summary. No agents invoked. |

Cold path actions still produce a `RouterContract` for consistency, but they skip the Planning AC phase since the scope is already narrow.

## Dispatch Flow

```
User query
  |
  v
Router.classify(query) --> Intent
  |
  +--- swarm_worthy? ---> Swarm workflow (see workflows/swarm.md)
  |
  +--- priority <= 3? ---> Hot path: AC Planning -> FullSearchPipeline
  |
  +--- priority 4-6?  ---> Cold path: direct agent dispatch
  |
  +--- priority 7?    ---> Cold path: SessionStore read-only query
  |
  v
RouterContract returned
  |
  v
Knowledge accumulation (if contract has kb_update_notes)
```

## RouterContract as Universal Response

Every dispatched workflow or agent call returns a `RouterContract`. The Router uses it to:

1. **Decide next action**: `is_approvable()` gates AC loop progression. `is_executable()` confirms a stage completed without blocking issues.
2. **Track blocking issues**: If `blocking = True`, the pipeline halts and the user is notified.
3. **Accumulate knowledge**: Non-empty `kb_update_notes` are passed to `KnowledgeManager.update_from_contract()`.
4. **Record audit trail**: The contract fields are logged to `SessionStore.record_event()` for every significant dispatch.

```python
class RouterContract(BaseModel):
    status: ContractStatus       # PLANNED, APPROVED, REQUEST_CHANGES, BLOCKED, EXECUTED, ESCALATE, SWARM_COMPLETE
    confidence: float            # 0-100 scale
    critical_issues: int         # Count of blocking problems
    blocking: bool               # Halts pipeline if True
    kb_update_notes: str         # Written to memory/patterns.md on completion
    evidence: str                # Free-text reasoning or feedback
```

## Knowledge Accumulation

After every completed loop (AC approval, Swarm completion, or cold-path execution), the Router checks the returned `RouterContract` for knowledge updates:

```
RouterContract.kb_update_notes != ""
  |
  v
KnowledgeManager.update_from_contract(kb_update_notes, evidence)
  |
  v
memory/patterns.md  (append under "## Learned Patterns")
```

Additionally, after a full pipeline run completes:

```
KnowledgeManager.record_progress(run_id, summary)
  |
  v
memory/progress.md  (append under "## Pipeline Runs")
```

This feedback loop means every pipeline run makes future runs smarter. Learned patterns inform search planning, outreach tone, and industry-specific strategies.

## Session Lifecycle

The Router manages `SessionStore` sessions for the hot path:

```
1. Router.classify(query) --> Intent
2. SessionStore.create_session(query) --> run_id
3. PipelineContext.new(query) --> ctx (ctx.run_id = run_id)
4. Dispatch workflow/agents...
5. SessionStore.save_companies(run_id, ...)
6. SessionStore.save_contacts(run_id, ...)
7. SessionStore.save_drafts(run_id, ...)
8. SessionStore.end_session(run_id, status="completed")
```

If any stage produces a `BLOCKED` or `ESCALATE` contract, the session is ended with `status="failed"` and the blocking event is recorded.

## Key Design Decisions

1. **Single entry point.** Every user interaction flows through the Router. There is no way to invoke an agent directly without Router mediation. This guarantees consistent intent classification, session tracking, and knowledge feedback.
2. **Priority as dispatch key.** The 7-level priority system cleanly separates hot-path (full pipeline) from cold-path (targeted agent) dispatch without complex conditional logic.
3. **Contracts everywhere.** Using `RouterContract` as the universal response type means the Router never has to special-case agent outputs. Every response is inspectable with the same fields.
4. **Swarm is an overlay, not a replacement.** When `swarm_worthy` is `True`, the Swarm replaces Discovery + Research but the rest of the pipeline (Skills, Contact, Resume, Outreach) still runs normally.
5. **Read-only REVIEW path.** Priority 7 queries never invoke agents or consume API tokens. They only read from `SessionStore`, making them cheap and safe for status checks.
