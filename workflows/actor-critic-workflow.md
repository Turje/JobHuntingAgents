# Actor-Critic Workflow

Quality assurance loops that ensure search plans and outreach drafts meet a minimum bar before advancing through the pipeline. Each phase pairs an **Actor** (the producing agent) with a **Critic** (the reviewing agent) and runs up to 3 revision cycles.

## Phases

### Phase 1 -- Planning (SearchPlanner / SearchCritic)

The Planning phase fires immediately after the Router classifies intent. Its job is to produce a validated search plan before any agents begin discovery work.

| Step | Agent | Action |
|------|-------|--------|
| 1 | SearchPlanner (Actor) | Generates a candidate search plan from the classified `Intent` (priority, domain, raw query). |
| 2 | SearchCritic (Critic) | Reviews the plan and returns a `RouterContract`. |
| 3 | Router | Reads the contract: if `APPROVED`, proceed to FullSearchPipeline. If `REQUEST_CHANGES`, send feedback back to the Planner. |

**Cycle states:**

```
PLANNED --> SearchCritic --> APPROVED  (proceed to pipeline)
                         \-> REQUEST_CHANGES  (re-plan with critic feedback)
```

The Planner receives the Critic's `evidence` field as explicit feedback so it can address each issue on the next attempt.

### Phase 2 -- Outreach (OutreachDrafter / OutreachCritic)

The Outreach phase runs after the pipeline has produced contacts, skill analyses, and resume tailoring. It ensures every cold email is personalized, professional, and compliant before marking it ready to send.

| Step | Agent | Action |
|------|-------|--------|
| 1 | OutreachDrafter (Actor) | Composes an `OutreachDraft` using `CompanyProfile`, `SkillsAnalysis`, `ContactInfo`, and `ResumeVersion` from `PipelineContext`. |
| 2 | OutreachCritic (Critic) | Reviews tone, personalization depth, compliance, and returns a `RouterContract`. |
| 3 | Router | If `APPROVED`, mark draft status as `approved`. If `REQUEST_CHANGES`, feed critic notes back to the Drafter. |

**Cycle states:**

```
DRAFT --> OutreachCritic --> APPROVED  (mark OutreachDraft.status = "approved")
                         \-> REQUEST_CHANGES  (revise with critic feedback)
```

## Cycle Budget

Both phases share the same ceiling: **max 3 cycles** per phase. If the Critic has not approved after 3 rounds, the contract status is set to `ESCALATE` and the Router logs a blocking event via `SessionStore.record_event`.

```
cycle 1: Actor produces --> Critic reviews
cycle 2: Actor revises  --> Critic reviews
cycle 3: Actor revises  --> Critic reviews
         (still not approved) --> ESCALATE
```

Escalation writes a structured event to the `events` table with `event_type = "escalation"` so it can be surfaced to the user or handled by a higher-level orchestrator.

## RouterContract Integration

Every Critic response is a `RouterContract` containing:

| Field | Role in AC Loop |
|-------|-----------------|
| `status` | `APPROVED` or `REQUEST_CHANGES` (or `ESCALATE` on budget exhaustion). |
| `confidence` | Numeric score (0--100). Must be >= 60 for `is_approvable()` to return `True`. |
| `critical_issues` | Count of blocking problems. The Actor should resolve all before the next cycle. |
| `blocking` | If `True`, the pipeline halts at this step until resolved. |
| `evidence` | Free-text feedback passed back to the Actor as revision instructions. |
| `kb_update_notes` | After approval, these notes are written to `memory/patterns.md` via `KnowledgeManager.update_from_contract`. |

### Approval Gate

A plan or draft advances only when both conditions hold:

```python
contract.status == ContractStatus.APPROVED
contract.confidence >= 60.0
```

This is encapsulated in `RouterContract.is_approvable()`.

## Data Flow

```
User query
  |
  v
Router (intent classification)
  |
  v
+----------------------------------+
| AC Phase 1: Planning             |
|  SearchPlanner <-> SearchCritic  |
|  max 3 cycles                    |
+----------------------------------+
  | APPROVED
  v
FullSearchPipeline
  Discovery -> Research -> Skills -> Contact -> Resume
  |
  v
+----------------------------------+
| AC Phase 2: Outreach             |
|  OutreachDrafter <-> OutreachCritic |
|  max 3 cycles (per draft)        |
+----------------------------------+
  | APPROVED
  v
Excel export -> [Gmail draft]
```

## Key Design Decisions

1. **Critic feedback is structured, not binary.** The `evidence` field gives the Actor actionable revision notes rather than a bare pass/fail.
2. **Hard cycle cap prevents runaway loops.** Three iterations is enough to refine without burning tokens.
3. **Knowledge accumulation happens on approval.** When a Critic approves, any `kb_update_notes` are persisted so future runs benefit from learned patterns.
4. **Each outreach draft gets its own AC loop.** If a pipeline produces 10 companies, there are 10 independent Outreach AC loops, each with its own 3-cycle budget.
