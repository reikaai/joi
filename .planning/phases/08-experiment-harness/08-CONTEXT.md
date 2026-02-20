# Phase 8: Experiment Harness - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an isolated experiment mode that controls every variable except tool interface design, with full capture for post-hoc review. This replaces the v1.0 eval infrastructure which had 5 systemic bugs (serialization, evaluator gaps, ceiling effects, no persona isolation, no timestamp control). Old eval code and artifacts can be removed entirely.

</domain>

<decisions>
## Implementation Decisions

### Variable isolation
- Core principle: every variable must be identical across experiment arms except the one being tested (tool interface design)
- Zero-persona mode: minimal system prompt with no Joi personality — tool interface is the only variable
- Fixed timestamps injected (no datetime.now()) for reproducibility
- Each scenario self-contained, no external context dependencies

### Scenario strategy
- Clean slate — do NOT reuse v1.0 scenarios. Design new, better scenarios from scratch
- v1.0 had ceiling effects (95%+ pass rates on easy scenarios) — new scenarios must actually differentiate
- Old tests/eval artifacts can be removed without hesitation
- Harder scenarios that test real decision boundaries (lessons from Phase 5: ambiguous intent, multi-tool coordination, implicit parameters)

### Capture & review format
- Dual capture: JSONL files + LangSmith traces
- JSONL for batch analysis in Claude Code (prompt, response text, tool calls, tokens, run metadata per scenario)
- LangSmith traces for interactive drill-down, annotated with variant and run ID
- Must support blind review workflow (Phase 10: read transcripts before seeing aggregate stats)

### Tooling approach
- Idiomatic approaches only — use pytest if it fits naturally, scripts only when idiomatic for the use case
- Don't create unnecessary one-off scripts; leverage existing test infrastructure patterns where they apply
- Parity check: confirm both tool variants can express all scenario behaviors before running experiments

### Claude's Discretion
- Zero-persona system prompt exact wording
- Scenario count, content, and difficulty distribution
- Parity check implementation approach
- JSONL schema and field details
- How to handle v1.0 eval code removal (partial cleanup vs full replace)
- pytest fixtures/conftest design
- LangSmith annotation strategy
- Statistical methodology for result comparison

</decisions>

<specifics>
## Specific Ideas

- "We need to make sure that all variables will be the same except those which we are experimenting with"
- "Don't be afraid to remove old tests/evals and its artifacts" — clean break from v1.0 eval code is explicitly approved
- Phase 5 exploration found signal on `hard_ambiguous` scenarios (p=0.006) — new scenario design should learn from what actually differentiated

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-experiment-harness*
*Context gathered: 2026-02-20*
