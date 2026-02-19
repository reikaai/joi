---
phase: 05-full-comparison
plan: 02
subsystem: testing
tags: [eval, experiment, hard-scenarios, fisher-exact, exploration-loop, statistical-comparison, tool-variants]

# Dependency graph
requires:
  - phase: 05-full-comparison
    plan: 01
    provides: "Initial comparison data, Fisher exact infrastructure, EXPLORATION.md Pivot 0"
  - phase: 04-isolated-variable-experiments
    provides: "Phase 4 reference data for additive null model decomposition"
  - phase: 02-eval-framework
    provides: "Eval infrastructure (conftest.py, stats.py, test_tasks.py, evaluators.py)"
provides:
  - "10 hard positive scenarios across 4 difficulty dimensions"
  - "4 hard negative scenarios testing scheduling boundary cases"
  - "660 LLM calls across 3 exploration pivots with statistical analysis"
  - "REJECT recommendation for applike variant backed by p=0.006 significance on ambiguous intent"
  - "Complete EXPLORATION.md lab notebook ready for Phase 6 ADR"
affects: [06-adr]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Iterative exploration loop with per-pivot documentation and stopping criteria"]

key-files:
  created: []
  modified:
    - tests/eval/scenarios/tasks_positive.yaml
    - tests/eval/scenarios/tasks_negative.yaml
    - .planning/phases/05-full-comparison/EXPLORATION.md
    - tests/eval/reports/latest.json

key-decisions:
  - "REJECT applike variant: significant accuracy penalty on ambiguous intent (-36.7%, p=0.006)"
  - "Tool decomposition (one tool -> two tools) hurts Haiku 4.5 on ambiguous routing decisions"
  - "Coherent app framing provides mild synergy on easy tasks but compounds negatives on hard tasks"
  - "Stopped after Pivot 2 per criterion #2: >10% significant difference across 2+ categories"
  - "hard_implicit scenarios (before_weekend, usual_morning) are genuinely too hard for both -- floor effect, not interface effect"

patterns-established:
  - "Iterative exploration with stopping criteria: convergence, clear signal, null signal, budget cap"
  - "Hard scenario design across difficulty dimensions: ambiguous, multi, distractor, implicit"
  - "Type II error detection via rep count increase: Pivot 1 null was insufficient power, Pivot 2 revealed signal"

requirements-completed: [EXPR-03]

# Metrics
duration: 35min
completed: 2026-02-19
---

# Phase 05 Plan 02: Hard Scenario Exploration and Recommendation Summary

**REJECT applike: 660 LLM calls across 3 pivots find -36.7% accuracy on ambiguous intent (p=0.006); tool decomposition creates routing tax that Haiku 4.5 cannot absorb**

## Performance

- **Duration:** 35 min
- **Started:** 2026-02-19T18:25:48Z
- **Completed:** 2026-02-19T19:00:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Designed 14 hard scenarios across 4 difficulty dimensions (ambiguous, multi, distractor, implicit) plus 4 hard negatives
- Executed 3 exploration pivots totaling 660 LLM calls ($2.25 total cost)
- Found statistically significant applike deficit on hard_ambiguous: 53.3% baseline vs 16.7% applike (p=0.006)
- Produced clear REJECT recommendation with evidence synthesis, Phase 4 decomposition, and cumulative data table
- Demonstrated iterative exploration methodology: ceiling effect -> hard scenarios -> Type II error detection -> clear signal

## Task Commits

Each task was committed atomically:

1. **Task 1: Design hard scenarios and run exploration loop** - `a596fe5` (feat)
2. **Task 2: Produce final recommendation and complete EXPLORATION.md** - `b7c0046` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `tests/eval/scenarios/tasks_positive.yaml` - Added 10 hard positive scenarios across ambiguous, multi, distractor, implicit dimensions
- `tests/eval/scenarios/tasks_negative.yaml` - Added 4 hard negative scenarios (hedging, statement, question, past reference)
- `.planning/phases/05-full-comparison/EXPLORATION.md` - Complete lab notebook with 3 pivots, conclusion, cumulative data table
- `tests/eval/reports/latest.json` - Latest experiment data (Pivot 2: hard scenarios, 10 reps)

## Decisions Made
- Designed hard scenarios to target 4 dimensions identified in RESEARCH.md: ambiguous intent, multi-tool routing, distractor context, implicit parameters
- Ran Pivot 1 at 5 reps (matching Phase 4 for consistency) -- appeared null at n=50 per variant
- Increased to 10 reps for Pivot 2 after observing that 5 reps was insufficient power -- revealed the real signal hidden by Type II error
- Stopped exploration after Pivot 2: met stopping criterion #2 (>10% significant difference across 2+ categories)
- hard_implicit scenarios (before_weekend, usual_morning) are floor-effect scenarios -- both variants fail equally, tool interface irrelevant

## Deviations from Plan

None - plan executed exactly as written. The exploration loop followed the prescribed stopping criteria, and the EXPLORATION.md was updated incrementally per pivot as specified.

## Issues Encountered
- Pivot 1 showed an apparent null result (58.0% both variants) that could have led to premature "no difference" conclusion. Resolved by following the plan's rep count escalation strategy -- Pivot 2 at 10 reps revealed the real signal.
- `multi:two_reminders` easy scenario showed 0% applike (down from 40% in Pivot 0) -- high variance at n=5, consistent with the broader multi-tool routing tax finding.
- `hard_implicit:usual_morning` triggers `recall()` and `run_code()` on baseline instead of `schedule_task` -- the LLM interprets "the usual" as requiring memory lookup rather than scheduling. This is a prompt interpretation issue, not a tool interface issue.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- EXPLORATION.md contains complete evidence base for Phase 6 ADR
- Recommendation is unambiguous: REJECT applike, keep programmatic baseline
- Key evidence: hard_ambiguous p=0.006, hard positive aggregate p=0.029, cost neutral
- Open questions for ADR: model generalization (Sonnet/Opus), domain generalization, hybrid variants
- Cumulative data table at bottom of EXPLORATION.md provides single-reference for ADR author

## Self-Check: PASSED

- [x] tests/eval/scenarios/tasks_positive.yaml exists with 10 hard positive scenarios
- [x] tests/eval/scenarios/tasks_negative.yaml exists with 4 hard negative scenarios
- [x] .planning/phases/05-full-comparison/EXPLORATION.md contains Conclusion, Cumulative Data, REJECT, Pivot 1, Pivot 2
- [x] tests/eval/reports/latest.json exists with hard category data
- [x] Commit a596fe5 exists in git log
- [x] Commit b7c0046 exists in git log

---
*Phase: 05-full-comparison*
*Completed: 2026-02-19*
