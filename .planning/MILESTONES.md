# Milestones

## v1.0 Codebase Alignment & Tasks Experiment (Shipped: 2026-02-19)

**Phases completed:** 6 phases, 11 plans
**Timeline:** 17 days (2026-02-02 → 2026-02-19), ~90min execution
**Lines of code:** 8,584 Python (182 files changed, 38K insertions)
**Git range:** feat(02-01)..docs(v1) on `feat/arch1-gsd`

**Delivered:** Evidence-based decision discipline for Joi — audited codebase against strategic goals, built reusable eval framework, ran 960+ LLM calls across 6 tool variants, and produced ADR recommending REJECT of app-like tool interfaces.

**Key accomplishments:**
- 8x4 alignment scorecard identifying Memory as highest-impact misalignment, confirming tasks as first experiment target
- Reusable eval framework: YAML scenarios, decorator-based variant registry, LangSmith tracking, bootstrap BCa CIs
- 6 tool variants (4 isolated-variable + 1 app-like + baseline) with capability parity matrix
- 300 LLM calls: no isolated variable produces statistically significant improvement over 95% baseline
- REJECT app-like: 660 LLM calls, -36.7% accuracy on ambiguous intent (p=0.006) — tool decomposition creates routing tax under ambiguity
- 249-line ADR with root cause analysis and 5 generalization conditions for when to revisit

---

## v1.1 Eval Pipeline Rebuild & Re-validation (Shipped: 2026-02-20)

**Phases completed:** 4 phases, 5 plans
**Timeline:** 2026-02-20, ~21min execution
**Git range:** `4426a74`..`bd33a95` on `feat/arch1-gsd` (26 commits)
**Files:** 60 files changed, 5,827 insertions, 1,669 deletions

**Delivered:** Trustworthy experiment infrastructure and clean re-validation of tool interface decision — rebuilt eval pipeline from scratch with zero-persona isolation, ran 120 LLM calls, blind-reviewed every transcript, and confirmed REJECT of app-like interfaces with evidence that v1.0's routing penalty was a persona artifact.

**Key accomplishments:**
- Fixed AIMessage list-content serialization bug and wiped corrupted v1.0 eval cache
- Built zero-persona experiment infrastructure: simplified variants, JSONL capture, 7 parity tests, deleted 1,344 lines of v1.0 eval code
- Designed 20 difficulty-calibrated scenarios across 5 categories (sanity, ambiguous, routing, negative, implicit)
- Executed 120 LLM calls (2 variants x 20 scenarios x 3 runs) at temp 0.2 with 100% collection rate
- Blind-reviewed all 120 transcripts with 4-dimension rubric — REJECT confirmed: both variants 100% equivalent, v1.0 signal was persona artifact
- Key insight: tool parameter design influences LLM response style more than tool naming/decomposition

---

