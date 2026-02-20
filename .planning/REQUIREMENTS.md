# Requirements: Joi — Eval Pipeline Rebuild

**Defined:** 2026-02-20
**Core Value:** Trustworthy experiment results so we can make defensible decisions about tool interfaces

## v1.1 Requirements

Requirements for eval pipeline rebuild. Each maps to roadmap phases.

### Infrastructure (INFRA)

- [x] **INFRA-01**: Eval captures full response text + tool calls (fix serialization bug that discards list content)
- [x] **INFRA-02**: Corrupted v1.0 eval cache invalidated and re-recordable

### Capture & Review (CAPT)

- [x] **CAPT-01**: Experiment runs produce JSONL with full context (prompt, response text, tool calls, tokens, metadata) for Claude Code review
- [x] **CAPT-02**: Run metadata captured alongside results (model, git commit, timestamp, variant definitions)

### Experiment Harness (EXPR)

- [x] **EXPR-01**: Zero-persona experiment mode isolates tool interface as the only variable (minimal system prompt, no personality)
- [x] **EXPR-02**: Automated tool parity check verifies both variants can express all scenario behaviors
- [x] **EXPR-03**: Fixed timestamp injection for reproducible results (no datetime.now())
- [x] **EXPR-04**: Clean scenario set — self-contained, no external context dependencies, each tests one thing

### Strategy Selection (ANLS)

- [x] **ANLS-01**: Clean experiment data collected on both tool variants with fixed pipeline
- [ ] **ANLS-02**: Results reviewed via LangSmith annotations + Claude Code JSONL analysis (blind review protocol)
- [ ] **ANLS-03**: ADR updated or replaced with conclusions from clean data

## v1.2 Requirements

Deferred to future. Formalize after seeing experiment data.

- **EVAL-01**: Behavioral classifier (5 outcome types) for automated scoring
- **EVAL-02**: Per-scenario YAML scoring weights (encode patterns from manual review)
- **EVAL-03**: Golden-response unit tests per evaluator x variant
- **EVAL-04**: Multi-turn eval sequences (if clean single-turn data shows need)
- **EVAL-05**: Review CLI script for terminal-based JSONL analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM-as-judge per scenario | 25 scenarios — manual review is feasible and more accurate |
| Custom web UI for review | Solo dev, local-only. LangSmith + terminal + Claude Code is sufficient |
| Automated regression detection | Eval still being designed, baselines unreliable |
| Prompt optimization loops | Experiments test tool interfaces, not prompt quality |
| Full-agent E2E eval mode | 10-100x more expensive, not needed for tool comparison |
| DeepEval / Promptfoo | Already have a working framework, adding tools adds complexity |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 7 | Complete |
| INFRA-02 | Phase 7 | Complete |
| CAPT-01 | Phase 8 | Complete |
| CAPT-02 | Phase 8 | Complete |
| EXPR-01 | Phase 8 | Complete |
| EXPR-02 | Phase 8 | Complete |
| EXPR-03 | Phase 8 | Complete |
| EXPR-04 | Phase 8 | Complete |
| ANLS-01 | Phase 9 | Complete |
| ANLS-02 | Phase 10 | Pending |
| ANLS-03 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-20 after roadmap creation*
