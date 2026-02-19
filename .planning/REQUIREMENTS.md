# Requirements: Joi — Codebase Alignment & Tasks Experiment

**Defined:** 2026-02-19
**Core Value:** Validated architectural decisions backed by evidence, not gut feel

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Codebase Audit

- [ ] **AUDIT-01**: Audit all subsystems against the 4 strategic goals (manifesto, skills, breakaway, daily tool)
- [ ] **AUDIT-02**: Document which subsystems are misaligned with reasoning for each
- [ ] **AUDIT-03**: Produce prioritized fix list ranked by impact for future milestones

### Eval Infrastructure

- [ ] **EVAL-01**: Build eval framework with LangSmith experiment tracking (pytest plugin)
- [ ] **EVAL-02**: Implement statistical significance testing via scipy bootstrap
- [ ] **EVAL-03**: Include negative test cases (agent should NOT misuse tools)
- [ ] **EVAL-04**: Measure and compare token cost per tool variant (using Haiku for cost efficiency)
- [ ] **EVAL-05**: Design eval system for reuse across future experiments (not just tasks)

### Tool Interface Experiment

- [ ] **EXPR-01**: Define app-like tool variants (Calendar, Reminders, Alarms style interfaces)
- [ ] **EXPR-02**: Run isolated variable experiments (rename-only, simplify-only, description-only)
- [ ] **EXPR-03**: Compare app-like vs programmatic variants with statistical rigor

### Documentation

- [ ] **DOCS-01**: Write ADR documenting hypothesis, methodology, results, and architectural decision

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
| AUDIT-01 | — | Pending |
| AUDIT-02 | — | Pending |
| AUDIT-03 | — | Pending |
| EVAL-01 | — | Pending |
| EVAL-02 | — | Pending |
| EVAL-03 | — | Pending |
| EVAL-04 | — | Pending |
| EVAL-05 | — | Pending |
| EXPR-01 | — | Pending |
| EXPR-02 | — | Pending |
| EXPR-03 | — | Pending |
| DOCS-01 | — | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 0
- Unmapped: 12 ⚠️

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after initial definition*
