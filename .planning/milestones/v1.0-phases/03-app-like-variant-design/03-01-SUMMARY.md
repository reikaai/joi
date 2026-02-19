---
phase: 03-app-like-variant-design
plan: 01
subsystem: testing
tags: [langchain, tool-variants, eval, structured-tool, experiment-design]

# Dependency graph
requires:
  - phase: 02-eval-framework
    provides: "ToolVariant registry, @register decorator, eval infrastructure"
provides:
  - "4 isolated-variable tool variants (rename, simplify, description_a, description_b)"
  - "Extended ToolVariant with schedule_tool_names list support"
  - "5-variant VARIANTS dict for parametrized eval runs"
affects: [03-02-PLAN, 04-experiment-execution]

# Tech tracking
tech-stack:
  added: []
  patterns: [single-dimension-isolation, structured-tool-dynamic-desc, typed-when-param-merge]

key-files:
  created:
    - tests/eval/variants/tasks_rename.py
    - tests/eval/variants/tasks_simplify.py
    - tests/eval/variants/tasks_description_a.py
    - tests/eval/variants/tasks_description_b.py
  modified:
    - tests/eval/variants/registry.py

key-decisions:
  - "Rename variant uses identical descriptions/params to baseline with only function names changed"
  - "Simplify variant merges when+delay_seconds+recurring into typed when: int | str (validated pattern from old eval)"
  - "Description A uses structured What/When-to-use/How format per Anthropic guidance"
  - "Description B uses minimal one-liner + examples-only format"
  - "All isolated variants share baseline system prompt (no confounding)"
  - "All experimental variants exclude run_code (orthogonal to task scheduling)"

patterns-established:
  - "Single-dimension isolation: each variant changes exactly ONE variable from baseline"
  - "StructuredTool.from_function for schedule tool (dynamic desc), @tool for static tools"

requirements-completed: [EXPR-01]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 3 Plan 1: Isolated-Variable Tool Variants Summary

**4 tool variants (rename, simplify, description_a, description_b) each varying exactly one dimension from baseline, with registry extended for multi-tool support**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T09:43:42Z
- **Completed:** 2026-02-19T09:46:09Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended ToolVariant dataclass with `schedule_tool_names: list[str] | None` for future multi-tool variants (app-like split)
- Created 4 isolated-variable variants registered in VARIANTS dict alongside baseline
- Rename variant uses app-like names (calendar_create_event, calendar_list_events, calendar_update_event) with identical params/descriptions
- Simplify variant reduces schedule_task from 5 params to 3 via typed `when: int | str`
- Description A uses structured What/When-to-use/How format; Description B uses minimal examples-first
- All experimental variants exclude run_code and share baseline system prompt

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend ToolVariant registry for multi-tool variants** - `803d7e8` (feat)
2. **Task 2: Create 4 isolated-variable tool variants** - `a6517d5` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `tests/eval/variants/registry.py` - Added schedule_tool_names field and auto-imports for 4 new modules
- `tests/eval/variants/tasks_rename.py` - App-like names (calendar_*), identical params/descriptions to baseline
- `tests/eval/variants/tasks_simplify.py` - Merged timing params into typed when: int | str
- `tests/eval/variants/tasks_description_a.py` - Structured What/When-to-use/How description format
- `tests/eval/variants/tasks_description_b.py` - Minimal one-liner + examples-first description format

## Decisions Made
- Rename variant keeps baseline description text verbatim, only replacing function names in examples (isolates naming signal)
- Simplify list_tasks and update_task are identical to baseline (only schedule_task changes)
- Description A applies structured format to all 3 tools (list_tasks and update_task also get What/When/How)
- Description B applies minimal format to all 3 tools (terse single-line descriptions)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff import sorting in registry.py**
- **Found during:** Task 1 (Registry extension)
- **Issue:** Auto-import lines were not in alphabetical order per ruff I001
- **Fix:** Ran `ruff check --fix` to sort imports
- **Files modified:** tests/eval/variants/registry.py
- **Verification:** `ruff check tests/eval/variants/registry.py` passes
- **Committed in:** 803d7e8 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial import ordering fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 5 variants registered and ready for parametrized eval runs
- Plan 02 (full app-like variant) can build on the schedule_tool_names field added here
- Phase 4 experiment execution can use all variants immediately

## Self-Check: PASSED

All 5 created/modified files verified present. Both task commits (803d7e8, a6517d5) verified in git log.

---
*Phase: 03-app-like-variant-design*
*Completed: 2026-02-19*
