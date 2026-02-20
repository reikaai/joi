---
phase: 08-experiment-harness
verified: 2026-02-20T01:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 8: Experiment Harness Verification Report

**Phase Goal:** An isolated experiment mode exists that controls every variable except the one being tested (tool interface design), with full capture for post-hoc review
**Verified:** 2026-02-20T01:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Plan 01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Zero-persona system prompt exists as a constant with no Joi personality, no tool name references | VERIFIED | `ZERO_PERSONA` in `conftest.py` — all 7 tool names absent, no Joi personality markers |
| 2 | Both tool variants (baseline, applike) registered and produce working tool lists via tools_factory() | VERIFIED | `VARIANTS` dict loads with both keys; `tools_factory()` callable on both |
| 3 | JSONL writer produces valid JSONL with run_metadata line and scenario_result lines | VERIFIED | End-to-end test confirms `type` field, `run_id`, `git_commit`, all required keys |
| 4 | Parity tests pass confirming both variants can schedule one-time, recurring, list, and update | VERIFIED | 7/7 parity tests pass (`uv run pytest tests/experiment/parity.py -v -m experiment`) |
| 5 | Fixed timestamp constant exists and is used for all scenario invocations (no datetime.now()) | VERIFIED | `FIXED_TIMESTAMP = "2026-02-15 10:00 UTC"` in conftest; `datetime.now` absent from conftest/scenarios/test_experiment |
| 6 | pytest 'experiment' marker is registered and usable | VERIFIED | `pyproject.toml` has `"experiment: marks tests as experiment harness tests (hits real API, captures JSONL)"` |

### Observable Truths (Plan 02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | Each scenario is self-contained — no external context, no references to prior conversation, tests one thing | VERIFIED | 20 scenarios reviewed — all use standalone natural language prompts with no prior-context references |
| 8 | Scenarios cover the full difficulty spectrum: sanity, ambiguous, routing, negative, implicit | VERIFIED | Distribution: 3 sanity, 6 ambiguous, 4 routing, 4 negative, 3 implicit — 20 total |
| 9 | The experiment test invokes ChatAnthropic.bind_tools().ainvoke() directly — no full agent graph | VERIFIED | `test_experiment.py:19-32` — `llm.bind_tools(...).ainvoke([...])` with no graph import |
| 10 | Every scenario execution writes a line to JSONL with prompt, response text, tool calls, and token counts | VERIFIED | `write_result()` call at line 63-73 includes all required fields |
| 11 | LangSmith traces are annotated with variant name, scenario category, and run ID | VERIFIED | `t.log_feedback` calls for variant, run_id, category, input_tokens, output_tokens |
| 12 | No assertions judge response correctness — capture only, no evaluator logic | VERIFIED | No executable `assert` statements in `test_experiment.py`; only a comment noting capture-only |
| 13 | Fixed timestamp is injected into every HumanMessage, datetime.now() never used for scenario content | VERIFIED | `HumanMessage(content=f"[{FIXED_TIMESTAMP}]\n{scenario.prompt}")` at line 35; grep confirms zero `datetime.now` in test/scenario/conftest |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/experiment/conftest.py` | Fixtures: run_id, jsonl_writer, FIXED_TIMESTAMP, ZERO_PERSONA, EVAL_MODEL | VERIFIED | All constants and fixtures present; jsonl_writer yields JSONLWriter with close() teardown |
| `tests/experiment/capture.py` | JSONLWriter with write_metadata() and write_result() | VERIFIED | Class with constructor, write_metadata, write_result, close — JSONL schema validated |
| `tests/experiment/variants/registry.py` | ToolVariant dataclass (no persona), VARIANTS dict | VERIFIED | Dataclass has name, tools_factory, schedule_tool_name, schedule_tool_names, description — no persona field |
| `tests/experiment/variants/baseline.py` | schedule_task, list_tasks, update_task | VERIFIED | Three tools; schedule_task has 5 params including recurring |
| `tests/experiment/variants/applike.py` | calendar_create_event, reminders_create, calendar_list_events, calendar_update_event | VERIFIED | Four tools; reminders_create has schedule param for recurring |
| `tests/experiment/parity.py` | 7 static parity tests | VERIFIED | 7 test functions, all marked @pytest.mark.experiment, all pass |
| `tests/experiment/scenarios.py` | Frozen Scenario dataclass, SCENARIOS list with 15-20 scenarios | VERIFIED | 20 scenarios, frozen dataclass, 5 categories, all IDs unique in category:name format |
| `tests/experiment/test_experiment.py` | Parametrized experiment test: variant x scenario matrix | VERIFIED | 40 items collected (2 variants x 20 scenarios), async, dual-capture, no assertions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `conftest.py` | `capture.py` | `jsonl_writer` fixture creates JSONLWriter | VERIFIED | `from tests.experiment.capture import JSONLWriter` at line 6; fixture instantiates it |
| `registry.py` | `baseline.py` | auto-import triggers registration | VERIFIED | `import tests.experiment.variants.baseline` at bottom of registry.py |
| `registry.py` | `applike.py` | auto-import triggers registration | VERIFIED | `import tests.experiment.variants.applike` at bottom of registry.py |
| `parity.py` | `registry.py` | VARIANTS dict import for schema inspection | VERIFIED | `from tests.experiment.variants.registry import VARIANTS, ToolVariant` |
| `test_experiment.py` | `conftest.py` | fixtures: run_id, jsonl_writer, ZERO_PERSONA, FIXED_TIMESTAMP, EVAL_MODEL | VERIFIED | Module-level import of constants; pytest fixtures used by signature |
| `test_experiment.py` | `registry.py` | VARIANTS dict for parametrization | VERIFIED | `from tests.experiment.variants.registry import VARIANTS` |
| `test_experiment.py` | `scenarios.py` | SCENARIOS list for parametrization | VERIFIED | `from tests.experiment.scenarios import SCENARIOS` |
| `test_experiment.py` | `capture.py` | jsonl_writer fixture uses JSONLWriter | VERIFIED | `jsonl_writer.write_result(...)` called at lines 63-73 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EXPR-01 | 08-01, 08-02 | Zero-persona experiment mode isolates tool interface as only variable | SATISFIED | ZERO_PERSONA constant with no tool names, no Joi personality; injected as SystemMessage |
| EXPR-02 | 08-01 | Automated tool parity check verifies both variants can express all scenario behaviors | SATISFIED | 7 parity tests in parity.py all pass; covers schedule, recurring, list, update, params, no-persona, count |
| EXPR-03 | 08-01, 08-02 | Fixed timestamp injection for reproducible results (no datetime.now()) | SATISFIED | FIXED_TIMESTAMP = "2026-02-15 10:00 UTC"; datetime.now absent from test/scenario/conftest |
| EXPR-04 | 08-02 | Clean scenario set — self-contained, no external context, each tests one thing | SATISFIED | 20 scenarios verified as self-contained; each covers one decision boundary |
| CAPT-01 | 08-01, 08-02 | JSONL with full context (prompt, response text, tool calls, tokens, metadata) | SATISFIED | write_result fields: variant, scenario_id, category, prompt, response_text, tool_calls, input/output/total_tokens |
| CAPT-02 | 08-01, 08-02 | Run metadata captured alongside results (model, git commit, timestamp, variant definitions) | SATISFIED | write_metadata produces: type, run_id, git_commit, timestamp, model, fixed_timestamp, zero_persona, variants |

No orphaned requirements — all Phase 8 requirements (EXPR-01 through EXPR-04, CAPT-01, CAPT-02) appear in plan frontmatter and are satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `variants/baseline.py` | 22 | `return ""` from tool implementations | INFO | Expected — tools are stubs for LLM binding only; no side effects intended in experiment mode |
| `variants/applike.py` | multiple | `return ""` from tool implementations | INFO | Same as above — capture-only design, tool return values not evaluated |

No blockers. The empty returns are by design: tools are bound to the LLM for schema/routing purposes only; the experiment captures which tools the LLM selects, not what the tools do.

### Human Verification Required

#### 1. Actual API Run Produces Valid JSONL

**Test:** Run `uv run pytest tests/experiment/test_experiment.py -m experiment -k "sanity:explicit_onetime" -v` with a real ANTHROPIC_API_KEY set
**Expected:** One JSONL file appears in `results/`, containing a run_metadata line followed by two scenario_result lines (one per variant), each with non-empty response_text or tool_calls
**Why human:** Requires live API key and real network call; cannot verify without executing against Anthropic endpoint

#### 2. LangSmith Trace Annotation Quality

**Test:** After running one test item, inspect the LangSmith trace for the run
**Expected:** Trace shows inputs (prompt, variant, category, run_id, fixed_timestamp), outputs (response_text, tool_calls), and feedback tags (variant, run_id, category, token counts)
**Why human:** Requires LangSmith account access and visual inspection of trace UI

#### 3. Scenario Difficulty Calibration

**Test:** Run the full experiment and review JSONL output for sanity scenarios
**Expected:** Sanity scenarios (explicit_onetime, explicit_recurring, list_tasks) both variants achieve high tool invocation rate; ambiguous scenarios show measurable variance between variants
**Why human:** Requires actual LLM responses to assess whether difficulty calibration matches targets (90%+, 40-60%, etc.)

### Gaps Summary

None. All automated checks passed.

- 7/7 parity tests pass
- 40/40 experiment test items collected (no API calls needed for collection)
- Zero datetime.now() in test/scenario/conftest code
- Zero executable assertions in test_experiment.py
- JSONL schema produces all required fields
- Both tool variants register and produce working tool lists
- Zero-persona prompt contains no tool-specific names
- experiment marker registered in pyproject.toml
- results/ in .gitignore
- v1.0 cleanup complete — only stats.py remains in tests/eval/ (variants/ and reports/ dirs are empty pycache only)
- Commits 613ed64, 74b7dea, f43a912, a0f54be all verified in git history

---

_Verified: 2026-02-20T01:00:00Z_
_Verifier: Claude (gsd-verifier)_
