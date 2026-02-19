# Requirements: Joi — Codebase Alignment & Tasks Experiment

**Defined:** 2026-02-19
**Core Value:** Validated architectural decisions backed by evidence, not gut feel

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Codebase Audit

- [x] **AUDIT-01**: Audit all subsystems against the 4 strategic goals (manifesto, skills, breakaway, daily tool)
- [x] **AUDIT-02**: Document which subsystems are misaligned with reasoning for each
- [x] **AUDIT-03**: Produce prioritized fix list ranked by impact for future milestones

### Eval Infrastructure

- [x] **EVAL-01**: Build eval framework with LangSmith experiment tracking (pytest plugin)
- [x] **EVAL-02**: Implement statistical significance testing via scipy bootstrap
- [x] **EVAL-03**: Include negative test cases (agent should NOT misuse tools)
- [x] **EVAL-04**: Measure and compare token cost per tool variant (using Haiku for cost efficiency)
- [x] **EVAL-05**: Design eval system for reuse across future experiments (not just tasks)

### Tool Interface Experiment

- [x] **EXPR-01**: Define app-like tool variants (Calendar, Reminders, Alarms style interfaces)
- [x] **EXPR-02**: Run isolated variable experiments (rename-only, simplify-only, description-only)
- [x] **EXPR-03**: Compare app-like vs programmatic variants with statistical rigor

### Documentation

- [x] **DOCS-01**: Write ADR documenting hypothesis, methodology, results, and architectural decision

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Eval Enhancements

- **EVAL-06**: Real user scenario mining from Telegram conversation logs
- **EVAL-07**: Multi-model comparison (Haiku vs Sonnet vs Opus tool-use behavior)
- **EVAL-08**: Multi-turn error recovery testing (what happens when agent picks wrong tool)

### Tool Interface

- **EXPR-04**: Capability parity audit (ensure app tools cover all existing task features)
- **EXPR-05**: Token budget enforcement per tool definition
- **EXPR-06**: Implementation — actually rework tasks subsystem based on findings (if hypothesis validated)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Skills system implementation | Separate milestone — this milestone establishes evidence-based decision discipline first |
| PC Client / browser automation | Future milestone, depends on skills system |
| Media delegate improvements | Not misaligned, works fine as-is |
| Deployment / infra changes | Run locally only, not relevant to this milestone |
| Preserving old eval system | User explicitly okayed dropping existing evals in favor of new framework |
| Full agent E2E eval | Too expensive for hypothesis testing; single-step eval is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIT-01 | Phase 1: Codebase Alignment Audit | Complete |
| AUDIT-02 | Phase 1: Codebase Alignment Audit | Complete |
| AUDIT-03 | Phase 1: Codebase Alignment Audit | Complete |
| EVAL-01 | Phase 2: Eval Framework | Complete |
| EVAL-02 | Phase 2: Eval Framework | Complete |
| EVAL-03 | Phase 2: Eval Framework | Complete |
| EVAL-04 | Phase 2: Eval Framework | Complete |
| EVAL-05 | Phase 2: Eval Framework | Complete |
| EXPR-01 | Phase 3: App-Like Variant Design | Complete |
| EXPR-02 | Phase 4: Isolated Variable Experiments | Complete |
| EXPR-03 | Phase 5: Full Comparison | Complete |
| DOCS-01 | Phase 6: ADR and Decision | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after roadmap creation*
