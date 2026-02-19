---
phase: 02-eval-framework
plan: 01
subsystem: testing
tags: [yaml, dataclasses, eval, scenarios, variants]

requires:
  - phase: 01-codebase-alignment-audit
    provides: "Identified tasks subsystem as first experiment target"
provides:
  - "Typed Scenario/ScenarioAssertion dataclasses with YAML loader"
  - "ToolVariant dataclass and VARIANTS registry with register() decorator"
  - "Baseline variant matching production schedule_task interface"
  - "12 eval scenarios (7 positive, 5 negative) across 5 categories"
affects: [02-02, 02-03, eval-harness, experiment-runner]

tech-stack:
  added: [scipy, pyyaml]
  patterns: [yaml-driven-scenarios, decorator-based-registry]

key-files:
  created:
    - tests/eval/conftest.py
    - tests/eval/scenarios/tasks_positive.yaml
    - tests/eval/scenarios/tasks_negative.yaml
    - tests/eval/variants/registry.py
    - tests/eval/variants/tasks_baseline.py
  modified: []

key-decisions:
  - "YAML scenarios use typed dataclasses (Scenario, ScenarioAssertion) not raw dicts"
  - "Variant registry uses decorator pattern -- new variant = decorate a function in a new file"
  - "Baseline variant includes 4 tools (schedule_task, list_tasks, update_task, run_code) matching production"

patterns-established:
  - "Scenario-as-data: add eval cases via YAML edits, not Python code changes"
  - "Register decorator: @register('name') on a factory function auto-populates VARIANTS dict"
  - "Auto-import: registry.py imports variant modules at bottom to trigger registration"

requirements-completed: [EVAL-05]

duration: 2min
completed: 2026-02-19
---

# Phase 02 Plan 01: Eval Data Layer Summary

**YAML-driven scenario loader with typed dataclasses, decorator-based variant registry, and production-equivalent baseline variant**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T02:58:47Z
- **Completed:** 2026-02-19T03:00:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- 7 positive scenarios across 4 categories (single, sequence, multi, recurring) with typed assertions
- 5 negative scenarios for non-scheduling prompts
- Variant registry with register() decorator and ToolVariant typed dataclass
- Baseline variant reproducing production schedule_task interface (5 params, DESC_FIXED docstring)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create scenario YAML files and loader** - `c664d4f` (feat)
2. **Task 2: Create variant registry and baseline variant** - `1694ea5` (feat)

## Files Created/Modified
- `tests/eval/conftest.py` - Scenario/ScenarioAssertion dataclasses, load_scenarios() YAML loader
- `tests/eval/scenarios/tasks_positive.yaml` - 7 positive eval scenarios with assertions
- `tests/eval/scenarios/tasks_negative.yaml` - 5 negative eval scenarios (should NOT trigger tools)
- `tests/eval/variants/registry.py` - ToolVariant dataclass, VARIANTS dict, register() decorator
- `tests/eval/variants/tasks_baseline.py` - Baseline variant with 4 production-equivalent tools

## Decisions Made
- Used typed dataclasses over raw dicts for scenario/assertion representation -- enables IDE autocomplete and static analysis
- Variant registry uses decorator pattern (not manual dict population) -- mirrors existing TOOL_VARIANTS pattern but with typed structure
- Baseline variant includes all 4 tools (schedule_task + 3 companions) to match production evaluation context

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff lint violations in registry.py**
- **Found during:** Task 2 (variant registry)
- **Issue:** Unused `field` import and deprecated `typing.Callable` (should be `collections.abc.Callable`)
- **Fix:** Removed unused import, switched to `collections.abc.Callable`
- **Files modified:** tests/eval/variants/registry.py
- **Verification:** `ruff check tests/eval/` passes
- **Committed in:** 1694ea5 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial import fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Scenario loader and variant registry ready for Plan 02 (eval harness/runner)
- Baseline variant can be used as reference for new experimental variants
- Adding scenarios or variants requires only YAML/Python file additions, no framework changes

## Self-Check: PASSED

- All 5 created files exist on disk
- Both task commits (c664d4f, 1694ea5) found in git log

---
*Phase: 02-eval-framework*
*Completed: 2026-02-19*
