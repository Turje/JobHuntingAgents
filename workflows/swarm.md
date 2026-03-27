# Swarm Workflow

Parallel multi-company research that decomposes a broad query into independent research channels, executes them concurrently, and aggregates the results into a unified view.

## Purpose

When the user asks for wide-coverage research across many companies or an entire industry segment, a sequential agent-by-agent pipeline is too slow. The Swarm workflow fans out discovery and research into parallel `SwarmChannel` tasks, collects `SwarmResult` findings from each, and merges them back for downstream pipeline stages.

## When the Swarm Activates

The Router flags a query as swarm-worthy by setting `Intent.swarm_worthy = True`. Detection relies on keyword signals in the raw query:

| Indicator Keyword | Example Query |
|-------------------|---------------|
| `comprehensive` | "Give me a comprehensive overview of ML startups in climate tech" |
| `thorough` | "Do a thorough search of Series A fintech companies in NYC" |
| `deep dive` | "Deep dive into the sports tech space" |
| `all companies` | "Find all companies using PyTorch for computer vision" |
| `every` | "Research every edtech startup with recent funding" |
| `landscape` | "Map out the health tech landscape in Boston" |
| `survey` | "Survey the gaming industry for ML engineering roles" |

When `swarm_worthy` is `True`, the Router dispatches to the Swarm workflow instead of (or in addition to) the standard AC Planning phase. The resulting `SwarmResult` list feeds back into `PipelineContext.candidates` and `PipelineContext.profiles` for the rest of the pipeline.

## Channel Decomposition

The Swarm takes the initial set of 10--15 `CompanyCandidate` objects (produced by DiscoveryAgent or provided by the user) and creates one `SwarmChannel` per company.

### SwarmChannel Fields

```python
class SwarmChannel(BaseModel):
    channel_id: str       # Short UUID (8 chars) for tracking
    company_name: str     # Target company
    task_description: str # Specific research instructions for this channel
    agent_type: str       # "research" by default, can be "skills" or "contact"
```

Each channel is an independent unit of work with no cross-channel dependencies during execution. This isolation is what makes parallelism safe.

### Decomposition Strategy

```
User query: "Deep dive into sports tech AI companies"
  |
  v
DiscoveryAgent --> 12 CompanyCandidate objects
  |
  v
SwarmDecomposer:
  Channel-A: { company: "StatsBomb", task: "Research R&D, ML use cases, hiring signals" }
  Channel-B: { company: "Catapult",  task: "Research R&D, ML use cases, hiring signals" }
  Channel-C: { company: "Hawk-Eye",  task: "Research R&D, ML use cases, hiring signals" }
  ...
  Channel-L: { company: "Opta",     task: "Research R&D, ML use cases, hiring signals" }
```

## Parallel Execution

All channels are dispatched concurrently. Each channel runs the same research workflow (equivalent to what ResearchAgent does in the sequential pipeline) but scoped to a single company. Channels are independent and do not share state during execution.

```
[Channel-A] -------> SwarmResult-A
[Channel-B] -------> SwarmResult-B
[Channel-C] -------> SwarmResult-C
   ...                  ...
[Channel-L] -------> SwarmResult-L
        \                 /
         \               /
          v             v
        Aggregation Layer
```

## SwarmResult Fields

Each channel produces a `SwarmResult`:

```python
class SwarmResult(BaseModel):
    channel_id: str                    # Matches the originating SwarmChannel
    company_name: str                  # Company researched
    findings: str                      # Free-text research findings
    confidence: float                  # 0.0 - 1.0, how reliable the findings are
    cross_channel_insights: list[str]  # Observations relevant to other channels
```

The `cross_channel_insights` field captures information discovered about one company that is relevant to others (e.g., "StatsBomb and Opta share the same parent company" or "Catapult recently acquired a competitor in this list").

## Aggregation

After all channels complete, the aggregation layer:

1. **Collects all SwarmResults** and pairs them back to their originating channels.
2. **Calculates aggregate confidence** as the weighted mean of per-channel confidence scores.
3. **Extracts cross-channel insights** by collecting all `cross_channel_insights` entries and deduplicating them.
4. **Ranks results** by confidence to prioritize which companies advance to Skills, Contact, and Outreach stages.
5. **Produces a RouterContract** with:
   - `status = ContractStatus.SWARM_COMPLETE`
   - `confidence` = aggregate confidence (0--100 scale)
   - `critical_issues` = count of channels with confidence below 0.3
   - `kb_update_notes` = cross-channel insights summary for `KnowledgeManager`

## Integration with Pipeline

```
Router (swarm_worthy = True)
  |
  v
DiscoveryAgent --> CompanyCandidate list
  |
  v
SwarmDecomposer --> SwarmChannel per company
  |
  v
Parallel execution --> SwarmResult per channel
  |
  v
Aggregation --> ranked candidates + cross-channel insights
  |
  v
PipelineContext.candidates (updated with confidence)
PipelineContext.profiles   (populated from findings)
  |
  v
Standard pipeline continues: Skills -> Contact -> Resume -> Outreach
```

After aggregation, the pipeline continues with the normal sequential flow. The Swarm only replaces the Discovery + Research stages; downstream stages (Skills, Contact, Resume, Outreach) proceed as usual, now operating on the richer data the Swarm produced.

## Key Design Decisions

1. **Channel isolation.** No shared mutable state between channels. Cross-channel insights are collected after completion, not during execution.
2. **Confidence-based filtering.** Low-confidence results (< 0.3) are flagged as critical issues in the final `RouterContract`. The Router can choose to drop them or re-run those channels.
3. **Reuse of existing models.** `SwarmChannel` and `SwarmResult` live in `src/pylon/models.py` alongside all other Pydantic models, following the single-file convention.
4. **Bounded parallelism.** The channel count is capped by `SearchConfig.max_companies` (default 15) to prevent runaway API usage.
5. **Knowledge feedback.** Cross-channel insights are written to `memory/patterns.md` via `KnowledgeManager.update_from_contract` so future searches benefit from discovered relationships.
