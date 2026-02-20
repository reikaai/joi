# Phase 9: Run Experiments - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute both tool variants (baseline programmatic, app-like) against all clean scenarios from Phase 8 and collect captured data (JSONL + LangSmith traces) for human review in Phase 10. This phase produces data — analysis and decisions happen in Phase 10.

</domain>

<decisions>
## Implementation Decisions

### Execution strategy
- Run both variants in parallel (unless LangSmith rate limits require sequential)
- 3 runs per variant to surface non-deterministic LLM behavior
- Low temperature (0.2-0.3) — slight variance for realistic behavior while staying mostly consistent

### Run management
- pytest as the test runner (reuse Phase 8 experiment harness)
- Retry failed scenarios automatically — goal is clean data, not failure discovery
- Support rerunning a subset of scenarios (partial reruns) while retaining full history

### Output format
- Per-run JSONL files (e.g., baseline_run1.jsonl, applike_run2.jsonl) — NOT consolidated
- Separate files enable partial reruns without losing prior data
- History must be retained so runs can be compared across time
- LangSmith traces annotated with variant and run ID for every scenario execution

### Validation gates
- Run is complete when all scenarios in all runs have produced output
- No special validation beyond completeness — Phase 10 handles quality review

### Claude's Discretion
- Exact JSONL file naming convention and output directory structure
- Pytest fixtures and parametrization approach for multi-run execution
- Parallelization implementation (threading, subprocess, pytest-xdist, etc.)
- Whether to add a summary report after runs complete (scenario counts, timing)

</decisions>

<specifics>
## Specific Ideas

- "Sometimes we will rerun just a subset of evals, but we will need to retain the history so we can check back and compare"
- pytest felt like a natural runner given Phase 8 already uses it for the experiment harness

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-run-experiments*
*Context gathered: 2026-02-20*
