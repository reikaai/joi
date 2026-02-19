# Roadmap: Joi — Personal AI Agent

## Milestones

- ✅ **v1.0 Codebase Alignment & Tasks Experiment** — Phases 1-6 (shipped 2026-02-19)
- 🚧 **v1.1 Eval Pipeline Rebuild & Re-validation** — Phases 7-10 (in progress)

## Phases

<details>
<summary>✅ v1.0 Codebase Alignment & Tasks Experiment (Phases 1-6) — SHIPPED 2026-02-19</summary>

- [x] Phase 1: Codebase Alignment Audit (1/1 plans) — completed 2026-02-19
- [x] Phase 2: Eval Framework (3/3 plans) — completed 2026-02-19
- [x] Phase 3: App-Like Variant Design (2/2 plans) — completed 2026-02-19
- [x] Phase 4: Isolated Variable Experiments (2/2 plans) — completed 2026-02-19
- [x] Phase 5: Full Comparison (2/2 plans) — completed 2026-02-19
- [x] Phase 6: ADR and Decision (1/1 plan) — completed 2026-02-19

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Eval Pipeline Rebuild & Re-validation (In Progress)

**Milestone Goal:** Get trustworthy experiment results so we can make defensible decisions about tool interfaces. Fix the 5 systemic bugs that invalidated v1.0 data, rebuild the experiment harness with proper isolation, run clean experiments, and make a decision grounded in real evidence.

- [ ] **Phase 7: Infrastructure Fixes** — Fix serialization bug and invalidate corrupted cache so the measurement instrument works
- [ ] **Phase 8: Experiment Harness** — Build zero-persona isolated experiment mode with full capture, tool parity checks, clean scenarios, and fixed timestamps
- [ ] **Phase 9: Run Experiments** — Execute both tool variants against clean scenarios and collect JSONL for review
- [ ] **Phase 10: Review and ADR** — Review experiment data via LangSmith + Claude Code and produce ADR with defensible conclusions

## Phase Details

### Phase 7: Infrastructure Fixes
**Goal**: The eval pipeline produces correct, complete data — full response text and tool calls are captured, and no corrupted cache entries contaminate results
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Running an eval scenario that returns list-type AIMessage content produces JSONL with non-empty response text (the serialization bug that discarded all text to "" is fixed)
  2. No v1.0 cached responses are used — cache is invalidated and fresh responses are recorded on next run
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

### Phase 8: Experiment Harness
**Goal**: An isolated experiment mode exists that controls every variable except the one being tested (tool interface design), with full capture for post-hoc review
**Depends on**: Phase 7
**Requirements**: EXPR-01, EXPR-02, EXPR-03, EXPR-04, CAPT-01, CAPT-02
**Success Criteria** (what must be TRUE):
  1. Experiment mode runs with a minimal system prompt (no Joi persona, no personality) so tool interface is the only variable
  2. Running the parity check confirms both tool variants (baseline and app-like) can express all scenario behaviors — or flags gaps before experiments run
  3. All scenarios use injected fixed timestamps (no datetime.now()) so results are reproducible across runs
  4. Each scenario is self-contained, tests one thing, and has no external context dependencies
  5. Each experiment run produces a JSONL file containing prompt, response text, tool calls, tokens, and run metadata (model, git commit, timestamp, variant definitions) per scenario — sufficient for Claude Code batch review without re-running
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Run Experiments
**Goal**: Clean experiment data exists for both tool variants, collected with the fixed pipeline, ready for human review
**Depends on**: Phase 8
**Requirements**: ANLS-01
**Success Criteria** (what must be TRUE):
  1. Both tool variants (baseline programmatic, app-like) have been run against all clean scenarios with zero-persona mode
  2. JSONL files for both variants are available with full response text, tool calls, and metadata
  3. LangSmith traces exist for every scenario execution, annotated with variant and run ID
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

### Phase 10: Review and ADR
**Goal**: A defensible decision on tool interface strategy, grounded in manually-verified experiment data
**Depends on**: Phase 9
**Requirements**: ANLS-02, ANLS-03
**Success Criteria** (what must be TRUE):
  1. Every failure transcript has been read by a human (via LangSmith traces and/or JSONL) — no conclusions drawn from aggregate statistics alone
  2. Results reviewed using blind protocol (read transcripts before looking at aggregate pass rates)
  3. ADR exists documenting hypothesis, methodology, results from clean data, and a clear ADOPT/REJECT/REVISIT decision on tool interface strategy
**Plans**: TBD

Plans:
- [ ] 10-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Codebase Alignment Audit | v1.0 | 1/1 | Complete | 2026-02-19 |
| 2. Eval Framework | v1.0 | 3/3 | Complete | 2026-02-19 |
| 3. App-Like Variant Design | v1.0 | 2/2 | Complete | 2026-02-19 |
| 4. Isolated Variable Experiments | v1.0 | 2/2 | Complete | 2026-02-19 |
| 5. Full Comparison | v1.0 | 2/2 | Complete | 2026-02-19 |
| 6. ADR and Decision | v1.0 | 1/1 | Complete | 2026-02-19 |
| 7. Infrastructure Fixes | v1.1 | 0/? | Not started | - |
| 8. Experiment Harness | v1.1 | 0/? | Not started | - |
| 9. Run Experiments | v1.1 | 0/? | Not started | - |
| 10. Review and ADR | v1.1 | 0/? | Not started | - |
