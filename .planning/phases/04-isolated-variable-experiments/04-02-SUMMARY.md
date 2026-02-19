---
phase: 04-isolated-variable-experiments
plan: 02
subsystem: testing
tags: [eval, experiment, bootstrap-ci, statistical-analysis, tool-variants]

# Dependency graph
requires:
  - phase: 04-isolated-variable-experiments
    plan: 01
    provides: "Fixed evaluators for multi-tool variants and staggered timing"
  - phase: 02-eval-framework
    provides: "Eval infrastructure (conftest.py, stats.py, test_tasks.py)"
  - phase: 03-app-like-variant-design
    provides: "All 5 tool variants (baseline, rename, simplify, description_a, description_b)"
provides:
  - "Raw experiment data: 300 LLM calls across 5 variants with bootstrap CIs"
  - "Statistical comparisons: 10 pairwise with significance flags"
  - "Human-readable summary with per-variant interpretation"
affects: [05-run-and-analyze, 06-adr]

# Tech tracking
tech-stack:
  added: []
  patterns: ["pytest-repeat --count for statistical repetitions"]

key-files:
  created:
    - tests/eval/reports/latest.json
    - tests/eval/reports/phase4_summary.md
  modified: []

key-decisions:
  - "No isolated variable produces statistically significant improvement over baseline"
  - "Baseline already strong at 95% -- ceiling effect limits differentiability"
  - "Rename and simplify show non-significant negative trend (-3.3%)"
  - "Description rewrites (A and B) are indistinguishable from baseline and each other"

patterns-established:
  - "Experiment execution: unset LANGSMITH_TEST_CACHE, use --count=N for reps, target tests/eval/test_tasks.py directly"

requirements-completed: [EXPR-02]

# Metrics
duration: 20min
completed: 2026-02-19
---

# Phase 04 Plan 02: Run Isolated Variable Experiments Summary

**300 real LLM calls across 5 tool variants show no statistically significant accuracy differences; baseline already at 95%**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-19T16:56:43Z
- **Completed:** 2026-02-19T17:17:24Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- Ran 300 real LLM calls (5 variants x 12 scenarios x 5 reps) producing clean statistical data
- All 5 variants above 91.7% success rate with bootstrap BCa 95% CIs
- Generated comprehensive human-readable summary with per-variant interpretation and token cost analysis
- Key finding: no isolated variable (rename, simplify, description rewrite) produces a significant improvement

## Task Commits

Each task was committed atomically:

1. **Task 1: Run 5-variant experiment with statistical repetitions** - `3b2e6e1` (feat)
2. **Task 2: Generate human-readable Phase 4 summary report** - `c9415b4` (docs)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `tests/eval/reports/latest.json` - Raw JSON report with 5 variant stats and 10 pairwise comparisons
- `tests/eval/reports/phase4_summary.md` - Human-readable markdown summary with 7 sections

## Decisions Made
- Ran tests targeting `tests/eval/test_tasks.py` directly to avoid interference from older `test_task_scheduling_eval.py` (which also has `@pytest.mark.eval`)
- Used `--count=5` for 5 repetitions (300 total calls, ~$1.07) -- sufficient for narrow CIs
- Did not re-run with `--count=10` since CIs were already narrow enough (max spread ~15% on rename)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 23 test failures across 300 runs are real LLM behavior (not evaluator bugs): rename/simplify variants struggle with `multi:two_reminders` and some `recurring:morning` scenarios, `neg:past_tense_reminder` triggers false scheduling in rename/description_b variants. These are the exact phenomena the experiment is designed to measure.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Experiment data complete and ready for Phase 5 (combined applike variant comparison)
- Key signal for Phase 5: isolated changes don't help individually -- the question is whether the combined applike variant (which changes all variables simultaneously) performs differently
- Summary report ready for Phase 6 ADR consumption

## Self-Check: PASSED

- [x] tests/eval/reports/latest.json exists
- [x] tests/eval/reports/phase4_summary.md exists
- [x] Commit 3b2e6e1 exists in git log
- [x] Commit c9415b4 exists in git log

---
*Phase: 04-isolated-variable-experiments*
*Completed: 2026-02-19*
