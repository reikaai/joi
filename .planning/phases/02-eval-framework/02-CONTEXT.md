# Phase 2: Eval Framework - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a reusable eval harness that measures tool-use accuracy, token cost, and statistical significance. This is infrastructure for Phases 3-5 to run experiments on tool interface variants. No production code changes.

</domain>

<decisions>
## Implementation Decisions

### Experiment tracking
- LangSmith free tier is available and the user is curious about pytest integration
- Research should determine the best way to integrate LangSmith with the eval framework
- No paid services — free tier only

### LLM calls
- Real LLM calls using Haiku for eval runs (not mocked/recorded for primary experiments)
- Cost optimization: selective execution — only run new/changed experiments with real LLM calls
- Established baselines should use recorded results (cassettes or cached) to avoid re-running expensive calls
- The framework must support both modes: real calls for active experiments, cached for regression/established baselines

### Eval scenarios
- Invent realistic synthetic scenarios based on what the tasks subsystem does (scheduling, listing, updating, cron)
- No need to mine real Telegram conversations — realistic invented prompts are sufficient

### Claude's Discretion
- Scenario file format (YAML, JSON, Python fixtures — whatever works best)
- Variant registry design (how tool variants are defined and loaded)
- Results output format (terminal, files, both)
- Statistical analysis approach (bootstrap CI, etc.)
- How to implement the real-call vs cached-call dual mode
- Pytest plugin architecture vs standalone runner
- How to structure the eval package for reuse across future experiments

</decisions>

<specifics>
## Specific Ideas

- User wants tight iteration: `uv run pytest` should be the entry point
- Future-proofing matters: "we will have a ton of features" — framework must scale to many eval suites without re-running everything
- The eval framework itself is a portfolio artifact — it should demonstrate engineering maturity

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-eval-framework*
*Context gathered: 2026-02-19*
