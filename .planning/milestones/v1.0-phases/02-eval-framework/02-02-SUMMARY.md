---
phase: 02-eval-framework
plan: 02
subsystem: testing
tags: [langsmith, eval, pytest, caching, anthropic, haiku]

requires:
  - phase: 02-eval-framework
    provides: "Typed scenarios, variant registry, and baseline variant from plan 01"
provides:
  - "Reusable EvalResult dataclass with scores, token counts, pass/fail"
  - "evaluate_tool_calls() covering all assertion types (staggered_timing, has_timing, is_recurring, no_run_code)"
  - "Parametrized test_positive and test_negative with LangSmith feedback tracking"
  - "Dual-mode cache: LANGSMITH_TEST_CACHE=read|write for regression baselines"
affects: [02-03, experiment-runner, adr-generation]

tech-stack:
  added: []
  patterns: [langsmith-feedback-per-test, env-gated-cache, evaluator-as-module]

key-files:
  created:
    - tests/eval/evaluators.py
    - tests/eval/test_tasks.py
    - tests/eval/cache/.gitkeep
  modified:
    - .gitignore
    - pyproject.toml

key-decisions:
  - "Eval model hardcoded to claude-haiku-4-5-20251001 for cost-effective consistency"
  - "Cache keyed by variant_name/scenario_id with JSON serialization of AIMessage fields"
  - "Cache mode gated by LANGSMITH_TEST_CACHE env var: unset=real, read=cached, write=refresh"

patterns-established:
  - "Evaluator-as-module: assertion logic in evaluators.py, test orchestration in test_tasks.py"
  - "LangSmith feedback per test: log_inputs/outputs/reference_outputs/feedback for experiment tracking"
  - "Dual-mode cache: real calls for active experiments, cached for regression baselines"

requirements-completed: [EVAL-01, EVAL-03, EVAL-04]

duration: 5min
completed: 2026-02-19
---

# Phase 02 Plan 02: Eval Test Engine Summary

**Parametrized eval test suite with LangSmith experiment tracking, reusable evaluators, and dual-mode response caching**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T03:03:22Z
- **Completed:** 2026-02-19T03:08:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- EvalResult dataclass with correct_tool/correct_count scores, token counts, and failure messages
- evaluate_tool_calls() covering all 4 assertion types ported from existing eval
- test_positive/test_negative parametrized across variant registry and YAML scenarios
- LangSmith feedback logged per test: correct_tool, correct_count, no_false_trigger, token metrics
- Dual-mode cache: `LANGSMITH_TEST_CACHE=read` for fast regression, `write` to refresh baselines

## Task Commits

Each task was committed atomically:

1. **Task 1: Create evaluators module with reusable assertion logic** - `bc80683` (feat)
2. **Task 2: Create eval test file with LangSmith tracking** - `e33afdc` (feat)

## Files Created/Modified
- `tests/eval/evaluators.py` - EvalResult dataclass and evaluate_tool_calls() with all assertion types
- `tests/eval/test_tasks.py` - Parametrized test_positive/test_negative with LangSmith tracking and cache
- `tests/eval/cache/.gitkeep` - Cache directory placeholder (contents gitignored)
- `.gitignore` - Added tests/eval/cache/* exclusion
- `pyproject.toml` - Added langsmith marker to strict-markers config

## Decisions Made
- Hardcoded eval model to claude-haiku-4-5-20251001 for reproducibility and cost control
- Cache keyed by variant_name/scenario_id.json with simple JSON serialization
- Cache gated by env var (not CLI flag) for compatibility with CI and local workflows
- Added langsmith marker to pyproject.toml since strict-markers mode requires it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect eval model ID**
- **Found during:** Task 2 (test file verification)
- **Issue:** Plan specified `claude-haiku-4-5-20241022` which returns 404 from Anthropic API
- **Fix:** Changed to `claude-haiku-4-5-20251001` (current valid model ID)
- **Files modified:** tests/eval/test_tasks.py
- **Verification:** `uv run pytest -k "test_positive[single:reminder-baseline]" --count=1 -x` passes
- **Committed in:** e33afdc (Task 2 commit)

**2. [Rule 1 - Bug] Fixed ruff import sorting violation**
- **Found during:** Task 2 (ruff check)
- **Issue:** Import of `tests.eval.variants.tasks_baseline` placed after third-party imports triggered I001
- **Fix:** `ruff check --fix` reordered imports
- **Files modified:** tests/eval/test_tasks.py
- **Verification:** `ruff check tests/eval/test_tasks.py` passes
- **Committed in:** e33afdc (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Model ID fix was critical for functionality. Import fix was trivial. No scope creep.

## Issues Encountered
None

## User Setup Required
None - uses existing ANTHROPIC_API_KEY from environment.

## Next Phase Readiness
- `uv run pytest -m eval` runs the full eval suite
- `uv run pytest -m eval --collect-only` lists 12 test cases (7 positive + 5 negative for baseline)
- Cache populated for regression: `LANGSMITH_TEST_CACHE=read` skips LLM calls
- Ready for Plan 03 (experiment runner, statistical analysis, ADR generation)

## Self-Check: PASSED

- All 5 files exist on disk (evaluators.py, test_tasks.py, cache/.gitkeep, .gitignore, pyproject.toml)
- Both task commits (bc80683, e33afdc) found in git log

---
*Phase: 02-eval-framework*
*Completed: 2026-02-19*
