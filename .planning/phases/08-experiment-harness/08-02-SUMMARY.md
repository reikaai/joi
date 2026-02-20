---
phase: 08-experiment-harness
plan: 02
subsystem: testing
tags: [experiment, scenarios, parametrized-test, jsonl-capture, langsmith, capture-only]

# Dependency graph
requires:
  - phase: 08-experiment-harness
    plan: 01
    provides: "ToolVariant registry, JSONLWriter, conftest fixtures (ZERO_PERSONA, FIXED_TIMESTAMP, EVAL_MODEL, run_id, jsonl_writer)"
provides:
  - "20 experiment scenarios across 5 difficulty categories"
  - "Parametrized experiment test: 2 variants x 20 scenarios = 40 test items"
  - "Dual capture: JSONL write_result + LangSmith log_inputs/log_outputs/log_feedback"
  - "Capture-only test with zero evaluator assertions"
affects: [09-analysis, 10-evaluation]

# Tech tracking
tech-stack:
  added: []
  patterns: [frozen-scenario-dataclass, parametrized-variant-scenario-matrix, capture-only-test]

key-files:
  created:
    - tests/experiment/scenarios.py
    - tests/experiment/test_experiment.py
  modified: []

key-decisions:
  - "20 scenarios (not 15) to increase coverage of ambiguous and routing categories"
  - "Category distribution: 3 sanity, 6 ambiguous, 4 routing, 4 negative, 3 implicit — weighted toward differentiating categories"
  - "Scenario prompts designed as natural language without meta-instructions — tests real user phrasing"

patterns-established:
  - "Frozen Scenario dataclass with id (category:name), prompt, category, description"
  - "Parametrized test matrix: @pytest.mark.parametrize for variant_name x scenario cartesian product"
  - "Capture-only pattern: log everything, assert nothing — evaluation deferred to Phase 10"

requirements-completed: [EXPR-01, EXPR-03, EXPR-04, CAPT-01, CAPT-02]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 08 Plan 02: Experiment Scenarios & Test Summary

**20 difficulty-calibrated scenarios with parametrized capture-only test producing 40-item variant x scenario matrix with dual JSONL + LangSmith output**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T00:33:49Z
- **Completed:** 2026-02-20T00:36:46Z
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments
- Designed 20 self-contained scenarios across 5 difficulty categories calibrated from v1.0 failure analysis
- Built parametrized experiment test collecting 40 items (2 variants x 20 scenarios) with zero evaluator assertions
- Dual capture working: JSONL write_result with all fields + LangSmith annotation (variant, category, run_id, tokens)
- All 7 parity tests still pass, full lint clean, no datetime.now in test/scenario code

## Task Commits

Each task was committed atomically:

1. **Task 1: Design scenario set** - `f43a912` (feat)
2. **Task 2: Build experiment test** - `a0f54be` (feat)

## Files Created/Modified
- `tests/experiment/scenarios.py` - Frozen Scenario dataclass and SCENARIOS list with 20 scenarios across sanity/ambiguous/routing/negative/implicit
- `tests/experiment/test_experiment.py` - Parametrized async test: variant x scenario matrix with ChatAnthropic.bind_tools().ainvoke() and dual JSONL + LangSmith capture

## Decisions Made
- 20 scenarios instead of minimum 15 to provide better coverage of the ambiguous (6) and routing (4) categories that showed the most signal in v1.0
- Weighted category distribution toward differentiating categories (ambiguous 30%, routing 20%) vs sanity checks (15%)
- All prompts written as natural user phrasing without artificial complexity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete experiment harness ready: infrastructure (plan 01) + scenarios/test (plan 02)
- Phase 9 can execute experiments via `uv run pytest tests/experiment/test_experiment.py -m experiment`
- JSONL output lands in `results/` directory, LangSmith traces auto-annotated
- Phase 10 blind review supported: response text captured in both JSONL and LangSmith outputs

## Self-Check: PASSED

- FOUND: tests/experiment/scenarios.py
- FOUND: tests/experiment/test_experiment.py
- FOUND: .planning/phases/08-experiment-harness/08-02-SUMMARY.md
- FOUND: f43a912 (Task 1 commit)
- FOUND: a0f54be (Task 2 commit)

---
*Phase: 08-experiment-harness*
*Completed: 2026-02-20*
