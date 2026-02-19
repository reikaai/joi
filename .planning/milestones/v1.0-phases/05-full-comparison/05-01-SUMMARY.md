---
phase: 05-full-comparison
plan: 01
subsystem: testing
tags: [eval, experiment, fisher-exact, bootstrap-ci, statistical-comparison, tool-variants]

# Dependency graph
requires:
  - phase: 04-isolated-variable-experiments
    plan: 02
    provides: "Raw experiment data and Phase 4 reference statistics"
  - phase: 02-eval-framework
    provides: "Eval infrastructure (conftest.py, stats.py, test_tasks.py)"
  - phase: 03-app-like-variant-design
    provides: "Applike and baseline tool variants"
provides:
  - "Fisher exact test function in stats.py for binary outcome comparison"
  - "Per-category breakdown in report generation for granular analysis"
  - "Initial applike-vs-baseline comparison data (120 LLM calls)"
  - "EXPLORATION.md Pivot 0 with full statistical analysis and next steps"
affects: [05-02-hard-scenarios, 06-adr]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Fisher exact test for small-sample binary comparisons alongside bootstrap CI"]

key-files:
  created:
    - .planning/phases/05-full-comparison/EXPLORATION.md
  modified:
    - tests/eval/stats.py
    - tests/eval/evaluators.py
    - tests/eval/reports/latest.json

key-decisions:
  - "Applike shows -5.0% vs baseline (93.3% vs 98.3%) but not significant (Fisher p=0.364)"
  - "Per-category: multi-tool routing is the only dimension where applike underperforms (40% vs 80%)"
  - "Additive null model predicts 88.4%; actual 93.3% suggests slight positive synergy from coherent framing"
  - "Fixed evaluator _check_is_recurring to recognize applike schedule param (evaluator bug, not variant bug)"

patterns-established:
  - "Fisher exact + bootstrap CI dual reporting for all comparisons"
  - "EXPLORATION.md as living lab notebook with per-pivot documentation"

requirements-completed: [EXPR-03]

# Metrics
duration: 9min
completed: 2026-02-19
---

# Phase 05 Plan 01: Initial Applike-vs-Baseline Comparison Summary

**Fisher exact test added, 120 LLM calls show applike at 93.3% vs baseline 98.3% (not significant, p=0.364); multi-tool routing is the only differentiating dimension**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-19T18:13:24Z
- **Completed:** 2026-02-19T18:23:11Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `fisher_exact_comparison()` to stats.py for binary outcome comparison alongside bootstrap CI
- Enhanced `generate_report()` with per-category breakdown and Fisher exact in pairwise comparisons
- Ran 120 real LLM calls (2 variants x 12 scenarios x 5 reps) producing clean comparison data
- Created EXPLORATION.md with Pivot 0 documenting full analysis, additive null model, and next steps
- Fixed evaluator bug: `_check_is_recurring` now recognizes applike's `schedule` parameter for cron patterns

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Fisher exact test and per-category report breakdown** - `1021637` (feat)
2. **Task 2: Run initial applike-vs-baseline comparison and write Pivot 0** - `4a11596` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `tests/eval/stats.py` - Added `fisher_exact_comparison()`, per-category breakdown in `generate_report()`
- `tests/eval/evaluators.py` - Fixed `_check_is_recurring` to recognize `schedule` param
- `tests/eval/reports/latest.json` - Fresh comparison data with by_category and fisher_exact fields
- `.planning/phases/05-full-comparison/EXPLORATION.md` - Living lab notebook with Pivot 0 results

## Decisions Made
- Identified evaluator bug in `_check_is_recurring` during experiment: applike's `reminders_create` uses `schedule` param for cron, not `when`/`recurring`. Fixed inline (Rule 1 -- auto-fix bug).
- Did not re-run experiment after evaluator fix because `correct_tool_score` (used for report statistics) was already correct -- the bug only affected the `is_recurring` assertion check, not the tool-call detection metric.
- Baseline shifted from 95.0% (Phase 4) to 98.3% (Phase 5) -- within CI overlap, attributed to normal LLM sampling variance.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed evaluator _check_is_recurring for applike schedule param**
- **Found during:** Task 2 (running experiment)
- **Issue:** `_check_is_recurring` only checked `recurring=True` or cron in `when` field, but applike's `reminders_create` puts cron in `schedule` field. All applike recurring tests failed assertion despite correct behavior.
- **Fix:** Added `_looks_like_cron(args.get("schedule", ""))` to the check
- **Files modified:** `tests/eval/evaluators.py`
- **Verification:** Lint passes; assertion now correctly recognizes cron in schedule field
- **Committed in:** `4a11596` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for evaluator correctness. The scores in latest.json were not affected (correct_tool_score is independent of assertion checks). No scope creep.

## Issues Encountered
- 15 test assertion failures in the 120-call run: 10 from applike recurring scenarios (evaluator bug, fixed), 3 from applike multi:two_reminders (real LLM behavior -- applike struggles with multi-tool routing), 1 from baseline multi:two_reminders (used run_code instead of schedule_task), 1 from applike neg:past_tense_reminder (false trigger). These are genuine LLM behavioral differences, not infrastructure problems.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pivot 0 establishes the calibration baseline: no significant difference on easy scenarios
- Multi-tool routing identified as the key differentiating dimension for hard scenario exploration
- EXPLORATION.md ready for Plan 02 to continue with hard scenario design and exploration loop
- Report infrastructure (by_category, fisher_exact) ready for granular analysis in exploration pivots

## Self-Check: PASSED

- [x] tests/eval/stats.py contains fisher_exact_comparison
- [x] tests/eval/reports/latest.json contains by_category and fisher_exact fields
- [x] .planning/phases/05-full-comparison/EXPLORATION.md contains Pivot 0 section
- [x] Commit 1021637 exists in git log
- [x] Commit 4a11596 exists in git log

---
*Phase: 05-full-comparison*
*Completed: 2026-02-19*
