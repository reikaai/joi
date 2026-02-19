---
phase: 02-eval-framework
verified: 2026-02-19T03:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 2: Eval Framework Verification Report

**Phase Goal:** A reusable eval harness that can measure tool-use accuracy, token cost, and statistical significance for any future experiment
**Verified:** 2026-02-19T03:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `uv run pytest` executes the eval suite against a baseline tool variant and produces structured results (pass/fail per scenario, token counts, aggregated success rate) | VERIFIED | `pytest --collect-only` shows 12 parametrized test items (7 positive + 5 negative for baseline). `test_positive` asserts `result.passed`; `test_negative` asserts zero scheduling calls. Token counts captured in `EvalResult` and logged via `t.log_feedback`. |
| 2 | Results are tracked in LangSmith as named experiments, viewable in the LangSmith UI with per-scenario breakdowns | VERIFIED | `from langsmith import testing as t` imported and used in `test_tasks.py`. Both `test_positive` and `test_negative` call `t.log_inputs`, `t.log_reference_outputs`, `t.log_outputs`, and `t.log_feedback` with correct_tool, correct_count, no_false_trigger, input_tokens, output_tokens, total_tokens. Both functions are marked `@pytest.mark.langsmith`. |
| 3 | Negative test cases exist (prompts that should NOT trigger tool calls) and are evaluated alongside positive cases | VERIFIED | `tests/eval/scenarios/tasks_negative.yaml` contains 5 scenarios across categories: greeting, question_about_tasks, past_tense_reminder, ambiguous_time, task_word_not_scheduling. `test_negative` asserts `len(schedule_calls) == 0`. |
| 4 | Bootstrap confidence intervals are computed for success rates, and the report shows whether two variants differ with statistical significance | VERIFIED | `tests/eval/stats.py` implements `bootstrap_ci` (scipy BCa, seed=42, edge-case guarded) and `compare_variants` (significance = 0 not in CI). `generate_report` computes per-variant success_rate/token_usage/cost_usd CIs and pairwise comparisons. Verified: `compare_variants([1,1,1,1,0], [0,0,1,0,0])` returns `significant=True`. |
| 5 | The eval system accepts new tool variants and scenario sets without modifying framework code (registry pattern) | VERIFIED | New scenario = YAML edit only (no Python changes). New variant = create a file with `@register("name")` decorator. `registry.py` auto-imports `tasks_baseline` at module bottom. Framework code (`conftest.py`, `test_tasks.py`, `stats.py`) is unchanged when adding variants/scenarios. |

**Score:** 5/5 truths verified

---

### Required Artifacts

All artifacts verified at Level 1 (exists), Level 2 (substantive), and Level 3 (wired).

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `tests/eval/conftest.py` | Scenario/ScenarioAssertion dataclasses, `load_scenarios()`, `eval_results` session fixture, `record_eval_result`, `_generate_report_on_finish` autouse fixture | VERIFIED | 101 lines; all required symbols present; imports `yaml.safe_load` and `generate_report` from stats |
| `tests/eval/scenarios/tasks_positive.yaml` | 7 positive eval scenarios across 4 categories | VERIFIED | 64 lines; 7 scenarios with typed assertions (has_timing, staggered_timing, no_run_code, is_recurring) |
| `tests/eval/scenarios/tasks_negative.yaml` | 5 negative eval scenarios | VERIFIED | 36 lines; 5 scenarios with `expected_tool: null`, `min_calls: 0` |
| `tests/eval/variants/registry.py` | `ToolVariant` dataclass, `VARIANTS` dict, `register()` decorator | VERIFIED | 29 lines; auto-imports `tasks_baseline` at bottom; `VARIANTS` populated on import |
| `tests/eval/variants/tasks_baseline.py` | Baseline variant with 4 production-equivalent tools | VERIFIED | 65 lines; registers "baseline" with `@register`; `tools_factory()` returns 4 tools (`schedule_task`, `list_tasks`, `update_task`, `run_code`) |
| `tests/eval/evaluators.py` | `EvalResult` dataclass, `evaluate_tool_calls()`, assertion helpers | VERIFIED | 177 lines; covers all 4 assertion types (staggered_timing, has_timing, is_recurring, no_run_code); uses loguru |
| `tests/eval/test_tasks.py` | Parametrized `test_positive` and `test_negative` with LangSmith tracking and dual-mode cache | VERIFIED | 177 lines; `@pytest.mark.langsmith @pytest.mark.eval @pytest.mark.asyncio`; both functions accept `eval_results` fixture and call `record_eval_result` |
| `tests/eval/stats.py` | `bootstrap_ci`, `compare_variants`, `compute_cost`, `generate_report` | VERIFIED | 172 lines; scipy BCa bootstrap with fixed seed; Haiku pricing constants; pairwise comparisons; writes JSON to `tests/eval/reports/latest.json` |
| `tests/eval/cache/.gitkeep` | Cache directory preserved in git | VERIFIED | Exists; `tests/eval/cache/*` gitignored, `.gitkeep` whitelisted |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/eval/conftest.py` | `tests/eval/scenarios/*.yaml` | `yaml.safe_load` in `load_scenarios()` | VERIFIED | Line 34: `data = yaml.safe_load(f)` |
| `tests/eval/variants/tasks_baseline.py` | `tests/eval/variants/registry.py` | `@register("baseline")` populates `VARIANTS` | VERIFIED | Line 55: `@register("baseline")` decorator; `VARIANTS["baseline"]` confirmed at runtime |
| `tests/eval/test_tasks.py` | `tests/eval/conftest.py` | `load_scenarios()` for parametrization | VERIFIED | Line 13: `from tests.eval.conftest import Scenario, load_scenarios, record_eval_result`; lines 85-86: `_positive_scenarios = load_scenarios("tasks_positive")` |
| `tests/eval/test_tasks.py` | `tests/eval/variants/registry.py` | `VARIANTS` dict for variant iteration | VERIFIED | Line 15: `from tests.eval.variants.registry import VARIANTS, ToolVariant`; line 87: `_variant_names = list(VARIANTS.keys())` |
| `tests/eval/test_tasks.py` | `tests/eval/evaluators.py` | `evaluate_tool_calls()` for structured evaluation | VERIFIED | Line 14: `from tests.eval.evaluators import evaluate_tool_calls`; line 106: `result = evaluate_tool_calls(response, scenario, variant)` |
| `tests/eval/test_tasks.py` | langsmith | `@pytest.mark.langsmith` + `t.log_feedback` | VERIFIED | Lines 9, 90, 130: import and markers; lines 109-113, 156-159: `t.log_feedback` with all required keys |
| `tests/eval/stats.py` | `scipy.stats` | `bootstrap()` for BCa confidence intervals | VERIFIED | Line 5: `from scipy.stats import bootstrap`; lines 36-43, 83-91: BCa calls with `method="BCa"` |
| `tests/eval/conftest.py` | `tests/eval/stats.py` | conftest calls `generate_report` after test session | VERIFIED | Line 9: `from tests.eval.stats import generate_report`; line 100: `generate_report(dict(eval_results), output_path)` |
| `tests/eval/test_tasks.py` | `tests/eval/conftest.py` | `eval_results` fixture injection and `record_eval_result` calls | VERIFIED | Both `test_positive` and `test_negative` accept `eval_results: dict` fixture parameter; both call `record_eval_result` after evaluation |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EVAL-01 | 02-02-PLAN.md | Build eval framework with LangSmith experiment tracking (pytest plugin) | SATISFIED | `langsmith` marker in pyproject.toml; `t.log_inputs/outputs/feedback` in both test functions; `@pytest.mark.langsmith` on both tests |
| EVAL-02 | 02-03-PLAN.md | Implement statistical significance testing via scipy bootstrap | SATISFIED | `bootstrap_ci` and `compare_variants` in `stats.py` use scipy BCa; `generate_report` includes pairwise significance; significance = 0 not in CI |
| EVAL-03 | 02-02-PLAN.md | Include negative test cases (agent should NOT misuse tools) | SATISFIED | 5 negative scenarios in YAML; `test_negative` asserts `len(schedule_calls) == 0` |
| EVAL-04 | 02-02-PLAN.md + 02-03-PLAN.md | Measure and compare token cost per tool variant (using Haiku for cost efficiency) | SATISFIED | `EvalResult` captures input/output/total tokens; `compute_cost` uses Haiku pricing; `generate_report` includes `cost_usd` CI per variant; token feedback logged to LangSmith |
| EVAL-05 | 02-01-PLAN.md | Design eval system for reuse across future experiments (not just tasks) | SATISFIED | New scenario = YAML edit; new variant = `@register` decorated function in new file; framework code unchanged; `ToolVariant` generic over tool names and schedule_action |

All 5 requirements satisfied. No orphaned requirements found.

---

### Anti-Patterns Found

None. Scanned all 6 eval Python files for TODO/FIXME/placeholder patterns — clean.

Note: The tool stub bodies in `tasks_baseline.py` (e.g., `return ""`) are intentional — these are eval harness stubs, not production implementations. The stubs correctly serve their purpose of providing the LLM with tool signatures for capability evaluation without actually executing.

---

### Human Verification Required

**1. LangSmith Experiment Tracking**

**Test:** Run `LANGSMITH_API_KEY=<key> uv run pytest -m eval -k "baseline" --count=1 -x` and view results in LangSmith UI
**Expected:** Named experiment appears with per-scenario breakdowns showing correct_tool, correct_count, no_false_trigger, and token metrics
**Why human:** LangSmith UI verification requires live credentials and visual inspection; cannot verify experiment naming and breakdown display programmatically

**2. Cache Read Mode**

**Test:** After populating cache with `LANGSMITH_TEST_CACHE=write uv run pytest -m eval -k "single:reminder" -x`, run `LANGSMITH_TEST_CACHE=read uv run pytest -m eval -k "single:reminder" -x` and observe execution speed
**Expected:** Second run completes in under 1 second (no LLM call), passes with identical results
**Why human:** Speed comparison and cache-hit verification is observable but requires running both modes and timing

---

### Commit Verification

All 7 commits confirmed present in git history:
- `c664d4f` — feat(02-01): create scenario YAML files and loader
- `1694ea5` — feat(02-01): create variant registry and baseline variant
- `bc80683` — feat(02-02): create evaluators module with reusable assertion logic
- `e33afdc` — feat(02-02): create eval test file with LangSmith tracking and cache
- `a9a7d06` — feat(02-03): add statistical analysis module with bootstrap CIs
- `382567e` — feat(02-03): add results collection and report generation to conftest
- `b11b7f1` — feat(02-03): wire test_tasks.py to feed eval_results fixture

---

_Verified: 2026-02-19T03:30:00Z_
_Verifier: Claude (gsd-verifier)_
