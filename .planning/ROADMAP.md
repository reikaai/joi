# Roadmap: Joi — Codebase Alignment & Tasks Experiment

## Overview

This milestone establishes evidence-based decision discipline for Joi. It begins with a codebase audit against strategic goals, then builds eval infrastructure, designs tool interface variants, runs isolated and combined experiments, and culminates in an ADR documenting findings. Each phase has an approval gate — no phase proceeds without explicit sign-off. The only phase that touches production code is conditional on experimental results.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Codebase Alignment Audit** - Audit all subsystems against strategic goals, document misalignments, produce prioritized fix list (completed 2026-02-19)
- [ ] **Phase 2: Eval Framework** - Build reusable eval harness with experiment tracking, statistical rigor, negative cases, and token cost measurement
- [ ] **Phase 3: App-Like Variant Design** - Define tool variants (rename-only, simplify-only, description-only, full app) with capability parity audit
- [ ] **Phase 4: Isolated Variable Experiments** - Run single-variable experiments (rename, simplify, description) against baseline with statistical analysis
- [ ] **Phase 5: Full Comparison** - Run combined app-like variant vs programmatic baseline, interpret against isolated variable results
- [ ] **Phase 6: ADR and Decision** - Write Architecture Decision Record documenting hypothesis, methodology, results, and recommendation

## Phase Details

### Phase 1: Codebase Alignment Audit
**Goal**: Clear picture of which Joi subsystems serve the strategic goals and which need rework
**Depends on**: Nothing (first phase)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. Every Joi subsystem (graph, tools, memory, tasks, media delegate, context management, sandbox) has been evaluated against all 4 strategic goals with a clear aligned/misaligned/neutral verdict
  2. Each misalignment has a written reasoning explaining WHY it's misaligned (not just that it is)
  3. A prioritized fix list exists, ranked by impact, that can inform future milestone planning
  4. The tasks subsystem's position in the priority list validates (or challenges) the decision to experiment on it first
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md — Alignment matrix, misalignment reasoning, prioritized fix list, tasks-first validation

### Phase 2: Eval Framework
**Goal**: A reusable eval harness that can measure tool-use accuracy, token cost, and statistical significance for any future experiment
**Depends on**: Phase 1 (audit provides codebase understanding; approval gate)
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):
  1. Running `uv run pytest` executes the eval suite against a baseline tool variant and produces structured results (pass/fail per scenario, token counts, aggregated success rate)
  2. Results are tracked in LangSmith as named experiments, viewable in the LangSmith UI with per-scenario breakdowns
  3. Negative test cases exist (prompts that should NOT trigger tool calls) and are evaluated alongside positive cases
  4. Bootstrap confidence intervals are computed for success rates, and the report shows whether two variants differ with statistical significance
  5. The eval system accepts new tool variants and scenario sets without modifying framework code (registry pattern)
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Scenario YAML files, loader, variant registry, baseline variant
- [ ] 02-02-PLAN.md — Evaluators module, eval test file with LangSmith tracking
- [ ] 02-03-PLAN.md — Statistical analysis (bootstrap CI), report generation

### Phase 3: App-Like Variant Design
**Goal**: A set of well-defined tool interface variants ready to be measured, with no silent capability loss
**Depends on**: Phase 2 (need measurement infrastructure before creating things to measure)
**Requirements**: EXPR-01
**Success Criteria** (what must be TRUE):
  1. At least 4 tool variants exist in the variant registry: baseline (current tools), rename-only, simplify-only, description-only, and full app-like (Calendar/Reminders/Alarms decomposition)
  2. A capability parity matrix shows that every parameter and behavior of the current task tools is accounted for in the full app-like variant (no silent drops)
  3. Token budget measurement confirms the app-like tool definitions do not exceed current tool definitions by more than 10%
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Isolated Variable Experiments
**Goal**: Interpretable signal on which individual variable (naming, parameter simplification, description style) drives tool-use improvement
**Depends on**: Phase 3 (need variants defined before running experiments)
**Requirements**: EXPR-02
**Success Criteria** (what must be TRUE):
  1. Rename-only variant has been compared to baseline with bootstrap confidence intervals reported
  2. Simplify-only variant has been compared to baseline with bootstrap confidence intervals reported
  3. Description-only variant has been compared to baseline with bootstrap confidence intervals reported
  4. Each comparison has sufficient sample size for interpretable results (minimum 3 repeat runs per scenario)
  5. Results clearly show which variable(s) produce statistically significant improvement (or show no significant difference)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Full Comparison
**Goal**: Definitive answer on whether the combined app-like interface outperforms the programmatic interface, interpreted against isolated variable results
**Depends on**: Phase 4 (isolated results needed to interpret combined results)
**Requirements**: EXPR-03
**Success Criteria** (what must be TRUE):
  1. Full app-like variant has been compared to baseline with bootstrap confidence intervals and Fisher exact test (if sample is small)
  2. Token cost comparison shows cost-per-task for both variants
  3. Results are interpreted against Phase 4 isolated variable findings (e.g., "rename accounts for X% of the improvement, simplification accounts for Y%")
  4. A clear adopt/reject/hybrid recommendation exists, backed by the data
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: ADR and Decision
**Goal**: A permanent record of this experiment that informs future Joi development and serves as a portfolio artifact
**Depends on**: Phase 5 (need results to document)
**Requirements**: DOCS-01
**Success Criteria** (what must be TRUE):
  1. An ADR exists in `docs/` following standard format: context, hypothesis, methodology, results, decision, consequences
  2. The ADR includes the actual statistical results (not just "it was better" but confidence intervals, effect sizes, token costs)
  3. The decision section clearly states whether to proceed with tasks rework (and if so, which variant) or to preserve the current interface
  4. The ADR is understandable by someone who wasn't involved in the experiment (portfolio-quality writing)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Codebase Alignment Audit | 0/TBD | Complete    | 2026-02-19 |
| 2. Eval Framework | 3/3 | Complete | 2026-02-19 |
| 3. App-Like Variant Design | 0/TBD | Not started | - |
| 4. Isolated Variable Experiments | 0/TBD | Not started | - |
| 5. Full Comparison | 0/TBD | Not started | - |
| 6. ADR and Decision | 0/TBD | Not started | - |
