# Phase 5: Full Comparison - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Run combined app-like variant vs programmatic baseline. Start with the planned comparison, then pivot into an iterative exploration loop with harder scenarios. Produce a clear adopt/reject/hybrid recommendation backed by data. Document the journey in a single evolving notebook (EXPLORATION.md).

</domain>

<decisions>
## Implementation Decisions

### Experiment structure
- Two-phase approach: initial planned comparison first, then iterative exploration loop
- Initial comparison: applike vs baseline using existing scenario set (Claude picks rep count based on Phase 4 power analysis)
- Exploration loop follows: design harder scenarios, run, observe, pivot, repeat
- Budget: unlimited within reason — keep going until clear answer or diminishing returns

### Exploration loop design
- Focus on harder scenarios as the primary exploration dimension
- Hard scenario design is Claude's discretion — dimensions like ambiguous intent, multi-tool coordination, implicit parameters, distractor context
- Claude may prune existing scenarios that don't differentiate (100% across all variants) and replace with harder ones
- Autonomous execution with incremental EXPLORATION.md — user can watch progress but doesn't need to approve each pivot
- Each pivot documented as it happens (lab notebook style in single doc)

### Interpretation framework
- If combined applike also shows no difference on easy scenarios: dig deeper with hard scenarios
- If hard scenarios also show no difference: accept that as the answer — tool interface doesn't matter for this model/complexity
- If hard scenarios DO show a difference: that's the finding — document the boundary where interface matters
- Decompose combined results against Phase 4 isolated findings where possible

### Recommendation criteria
- Must produce a clear adopt/reject/hybrid recommendation
- Recommendation is both a personal decision AND portfolio-quality evidence (Phase 6 ADR formalizes it)
- Token cost comparison included (cost-per-task for both variants)

### Claude's Discretion
- Sample size / rep count for initial comparison (power analysis based on Phase 4 effect sizes)
- Hard scenario design — which dimensions, how many, how to balance
- Scenario pruning decisions based on Phase 4 variance data
- When to stop the exploration loop (diminishing returns heuristic)
- Statistical methods per comparison (bootstrap CI, Fisher exact, etc.)

</decisions>

<specifics>
## Specific Ideas

- "Not just build on top — remove stuff, change approaches, mix" — the exploration should feel like a real research process, not a rigid pipeline
- Phase 4 showed 95% baseline with no isolated variable producing significant change — this is the starting point
- EXPLORATION.md should read as a coherent journey, not a dump of test results

</specifics>

<deferred>
## Deferred Ideas

- Trying different models (Sonnet) to test model-sensitivity of tool interface effects — future experiment if warranted
- Hybrid variants (mix-and-match app names + programmatic params) — only if exploration points that direction
- Prompt surgery (minimal vs rich system prompts) — interesting but outside Phase 5 scope

</deferred>

---

*Phase: 05-full-comparison*
*Context gathered: 2026-02-19*
