---
phase: 04-isolated-variable-experiments
plan: 01
subsystem: testing
tags: [evaluator, multi-tool, staggered-timing, tool-variants]

# Dependency graph
requires:
  - phase: 02-eval-framework
    provides: "Evaluator infrastructure (evaluators.py, test_tasks.py)"
  - phase: 03-app-like-variant-design
    provides: "ToolVariant.schedule_tool_names field, applike variant"
provides:
  - "Fixed evaluators that correctly handle multi-tool variants (applike)"
  - "Generic staggered timing check without hardcoded tool names"
affects: [04-02, 05-run-and-analyze]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Multi-tool variant filtering via schedule_tool_names fallback"]

key-files:
  created: []
  modified:
    - tests/eval/evaluators.py
    - tests/eval/test_tasks.py

key-decisions:
  - "Kept variant param on _check_staggered_timing for signature consistency with sibling functions"
  - "Three-tier timing detection: delay_seconds -> int when -> distinct string when (covers all variants)"

patterns-established:
  - "schedule_tool_names fallback pattern: variant.schedule_tool_names or [variant.schedule_tool_name]"

requirements-completed: [EXPR-02]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 04 Plan 01: Fix Evaluator Bugs Summary

**Multi-tool schedule filtering and generic staggered timing check for all tool variants**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T16:49:38Z
- **Completed:** 2026-02-19T16:54:23Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Fixed evaluate_tool_calls() to use schedule_tool_names (plural) for multi-tool variants like applike
- Removed hardcoded tool name gates from _check_staggered_timing(), now works for any variant
- Fixed test_negative() to correctly detect false triggers for multi-tool variants
- Verified rename variant passes 11/12 scenarios (1 failure is LLM behavior, not evaluator bug)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix evaluator multi-tool and hardcoded-name bugs** - `67d6213` (fix)

**Plan metadata:** (pending)

## Files Created/Modified
- `tests/eval/evaluators.py` - Fixed evaluate_tool_calls() multi-tool filtering, removed hardcoded name gates from _check_staggered_timing()
- `tests/eval/test_tasks.py` - Fixed test_negative() multi-tool filtering

## Decisions Made
- Kept `variant` parameter on `_check_staggered_timing` unused — maintains consistent function signatures across all checker functions (`_check_has_timing`, `_check_is_recurring` also take variant). Avoids unnecessary churn.
- Three-tier timing detection order: delay_seconds first (baseline/rename), then int when (simplify/applike), then distinct string when (fallback). No tool-name gating needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Evaluators now correctly handle all 6 variants (baseline, rename, simplify, description_a, description_b, applike)
- Ready for 04-02 experiment execution
- Note: rename neg:past_tense_reminder fails due to LLM behavior (not evaluator) -- expected for experiment data

## Self-Check: PASSED

- [x] tests/eval/evaluators.py exists
- [x] tests/eval/test_tasks.py exists
- [x] 04-01-SUMMARY.md exists
- [x] Commit 67d6213 exists in git log

---
*Phase: 04-isolated-variable-experiments*
*Completed: 2026-02-19*
