---
phase: 03-app-like-variant-design
plan: 02
subsystem: testing
tags: [langchain, tool-variants, eval, app-like-decomposition, token-budget, parity-matrix]

# Dependency graph
requires:
  - phase: 03-app-like-variant-design
    plan: 01
    provides: "4 isolated-variable variants, extended ToolVariant with schedule_tool_names"
provides:
  - "Full app-like variant with Calendar/Reminders tool decomposition"
  - "Capability parity matrix across all 6 variants"
  - "Token budget measurement script for variant comparison"
  - "6-variant VARIANTS dict ready for parametrized experiment execution"
affects: [04-experiment-execution]

# Tech tracking
tech-stack:
  added: []
  patterns: [calendar-reminders-decomposition, persona-patching, token-measurement-via-langchain]

key-files:
  created:
    - tests/eval/variants/tasks_applike.py
    - tests/eval/parity_matrix.md
    - tests/eval/token_budget.py
  modified:
    - tests/eval/variants/registry.py

key-decisions:
  - "App-like splits schedule_task into calendar_create_event (one-shot) and reminders_create (recurring)"
  - "calendar_update_event absorbs retry_in, question, message into single detail param"
  - "Persona patching via regex replacement of Background Tasks section with Calendar & Reminders framing"
  - "Token budget measured via ChatAnthropic.get_num_tokens_from_messages -- applike at +3.3% vs baseline"
  - "10% budget applies to tool definitions only, system prompt measured separately"

patterns-established:
  - "Persona patching: regex-replace section headers to swap tool framing without touching other sections"
  - "Token measurement: subtract no-tools baseline from with-tools count for isolated tool definition cost"

requirements-completed: [EXPR-01]

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 3 Plan 2: App-Like Variant + Parity Matrix + Token Budget Summary

**Full Calendar/Reminders app-like variant with 4 tools, parity matrix across 9 capabilities x 6 variants, and token budget script confirming +3.3% overhead**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T09:48:40Z
- **Completed:** 2026-02-19T09:51:23Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created app-like variant splitting one-shot/recurring into `calendar_create_event` and `reminders_create`
- `calendar_update_event` simplified from 6 params to 3 (absorbing retry_in/question/message into detail)
- System prompt patched: "Background Tasks" section replaced with "Calendar & Reminders" app framing
- Parity matrix documents all 9 capabilities across 6 variants with parameter absorption notes
- Token budget script measures tool definitions + system prompt tokens for all variants
- App-like tool definitions confirmed at +3.3% vs baseline (well within 10% budget)

## Token Budget Results

| Variant | Tools | Prompt | Total | Delta |
|---|---|---|---|---|
| applike | 1100 | 1660 | 2761 | +3.3% |
| baseline | 1065 | 1607 | 2672 | +0.0% |
| description_a | 1180 | 1607 | 2787 | +10.8% |
| description_b | 969 | 1607 | 2576 | -9.0% |
| rename | 1007 | 1607 | 2614 | -5.4% |
| simplify | 956 | 1607 | 2563 | -10.2% |

## Task Commits

Each task was committed atomically:

1. **Task 1: Create full app-like variant with Calendar/Reminders decomposition** - `1d82d4a` (feat)
2. **Task 2: Create parity matrix and token budget measurement** - `4664d4f` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `tests/eval/variants/tasks_applike.py` - Full app-like variant: 4 tools, persona patching, split one-shot/recurring
- `tests/eval/variants/registry.py` - Added applike auto-import
- `tests/eval/parity_matrix.md` - 9 capabilities x 6 variants with absorption notes
- `tests/eval/token_budget.py` - Token measurement script with budget check

## Decisions Made
- App-like uses `when` as string-only param (not typed int|str like simplify) -- matches RESEARCH.md spec
- `calendar_update_event` uses `event_id` instead of `task_id` (consistent with Calendar app metaphor)
- Persona patching uses regex to replace the "## Background Tasks" section, preserving all other sections
- Token budget check applies only to tool definitions (not system prompt), since system prompt change is a separate design decision

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 variants registered and ready for Phase 4 experiment execution
- Token budget script can be re-run anytime to validate changes
- Parity matrix serves as reference for evaluator assertions in Phase 4
- Evaluator already handles `schedule_tool_names` list for multi-tool variants

## Self-Check: PASSED

All 4 created/modified files verified present. Both task commits (1d82d4a, 4664d4f) verified in git log.

---
*Phase: 03-app-like-variant-design*
*Completed: 2026-02-19*
