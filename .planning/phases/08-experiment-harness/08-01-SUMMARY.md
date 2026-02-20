---
phase: 08-experiment-harness
plan: 01
subsystem: testing
tags: [experiment, variants, jsonl, parity, langchain-tools]

# Dependency graph
requires:
  - phase: 07-infrastructure-fixes
    provides: "Clean eval cache and working content extraction"
provides:
  - "Simplified ToolVariant dataclass (no persona field)"
  - "Baseline and applike tool variants for experiments"
  - "JSONLWriter for JSONL capture output"
  - "Zero-persona system prompt constant"
  - "Fixed timestamp constant for deterministic scenarios"
  - "7 parity tests confirming variant coverage"
  - "experiment pytest marker"
affects: [08-02, 09-analysis, 10-evaluation]

# Tech tracking
tech-stack:
  added: []
  patterns: [register-decorator-auto-import, zero-persona-isolation, jsonl-capture]

key-files:
  created:
    - tests/experiment/conftest.py
    - tests/experiment/capture.py
    - tests/experiment/variants/registry.py
    - tests/experiment/variants/baseline.py
    - tests/experiment/variants/applike.py
    - tests/experiment/parity.py
  modified:
    - pyproject.toml
    - .gitignore

key-decisions:
  - "Removed persona field from ToolVariant — zero-persona isolation for experiment fairness"
  - "Removed run_code tool from baseline variant — orthogonal to scheduling experiment"
  - "Kept tests/eval/stats.py — reusable stats utilities for Phase 9-10"
  - "Deleted all v1.0 eval infrastructure (15 files, 1344 lines removed)"

patterns-established:
  - "register() decorator with auto-import at bottom of registry.py for variant registration"
  - "JSONLWriter with run_metadata + scenario_result line types"
  - "Zero-persona constant with no tool-specific names"

requirements-completed: [EXPR-01, EXPR-02, EXPR-03, CAPT-01, CAPT-02]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 08 Plan 01: Experiment Infrastructure Summary

**Simplified tool variants (baseline + applike) with zero-persona isolation, JSONL capture, and 7 passing parity tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T00:27:18Z
- **Completed:** 2026-02-20T00:31:17Z
- **Tasks:** 2
- **Files modified:** 7 created, 2 modified, 15 deleted

## Accomplishments
- Built complete experiment infrastructure: variants, capture, fixtures, and parity verification
- Both tool variants (baseline, applike) register and produce working tool lists without persona dependency
- 7 parity tests pass confirming both variants cover one-time scheduling, recurring, list, update, required params
- Cleaned up 1344 lines of v1.0 eval infrastructure, keeping only stats.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Create experiment infrastructure** - `613ed64` (feat)
2. **Task 2: Implement parity checks and clean up v1.0** - `74b7dea` (feat)

## Files Created/Modified
- `tests/experiment/variants/registry.py` - Simplified ToolVariant dataclass and VARIANTS dict with register() decorator
- `tests/experiment/variants/baseline.py` - Baseline variant: schedule_task, list_tasks, update_task (no run_code)
- `tests/experiment/variants/applike.py` - Applike variant: calendar_create_event, reminders_create, calendar_list_events, calendar_update_event
- `tests/experiment/capture.py` - JSONLWriter with write_metadata() and write_result() methods
- `tests/experiment/conftest.py` - EVAL_MODEL, FIXED_TIMESTAMP, ZERO_PERSONA constants + session fixtures
- `tests/experiment/parity.py` - 7 static parity tests verifying variant coverage
- `pyproject.toml` - Added experiment pytest marker
- `.gitignore` - Added results/ directory

## Decisions Made
- Removed persona field from ToolVariant for zero-persona isolation
- Removed run_code tool from baseline (orthogonal to scheduling)
- Kept tests/eval/stats.py as standalone reusable utility
- Deleted all v1.0 eval code per locked decision in research phase

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff lint errors in capture.py and registry.py**
- **Found during:** Task 1 (verification step)
- **Issue:** `timezone.utc` should be `UTC` alias (UP017), imports unsorted in registry.py (I001)
- **Fix:** Changed `timezone.utc` to `UTC` from `datetime`, sorted auto-imports alphabetically
- **Files modified:** tests/experiment/capture.py, tests/experiment/variants/registry.py
- **Verification:** `ruff check tests/experiment/` passes
- **Committed in:** 613ed64 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor lint compliance fix. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All experiment infrastructure ready for plan 02 (scenario design and test execution)
- VARIANTS dict with working tools_factory() for both variants
- JSONLWriter ready for JSONL capture
- Zero-persona and fixed timestamp constants available as fixtures

---
*Phase: 08-experiment-harness*
*Completed: 2026-02-20*
