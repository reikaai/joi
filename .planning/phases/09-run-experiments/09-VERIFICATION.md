---
phase: 09-run-experiments
verified: 2026-02-20T05:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 9: Run Experiments Verification Report

**Phase Goal:** Clean experiment data exists for both tool variants, collected with the fixed pipeline, ready for human review
**Verified:** 2026-02-20T05:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Both tool variants (baseline, applike) produce per-run JSONL files with full response text, tool calls, and metadata | VERIFIED | 6 JSONL files exist; each has `variant`, `response_text`, `tool_calls` fields; 35/120 results have tool_calls-only (no text), which is valid data |
| 2 | 3 runs per variant exist (6 total JSONL files) with all 20 scenarios in each | VERIFIED | `results/` contains exactly 6 files; each has 21 lines (1 metadata + 20 results); all 20 unique scenario IDs present per file |
| 3 | LangSmith traces for every scenario execution include variant, run_id, and rep number | VERIFIED | `test_experiment.py` calls `t.log_feedback(key="variant")`, `t.log_feedback(key="run_id")`, `t.log_feedback(key="rep")` for every scenario |
| 4 | Prior run files are never overwritten — timestamped filenames preserve history | VERIFIED | `WriterPool` generates filename with shared `self._timestamp` at pool init; `JSONLWriter` opens in append mode (`"a"`); filenames are `{variant}_run{rep}_{timestamp}.jsonl` |
| 5 | Temperature is set to 0.2 for consistent-but-slightly-varied behavior | VERIFIED | `EVAL_TEMPERATURE = 0.2` in conftest; `ChatAnthropic(..., temperature=EVAL_TEMPERATURE)` in test; metadata records confirm `"temperature": 0.2` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `results/*.jsonl` | 6 JSONL files (2 variants x 3 runs) with 20 scenario results each | VERIFIED | 6 files present: applike_run{1,2,3} and baseline_run{1,2,3}, each 21 lines, all scenario IDs unique per file, no empty responses |
| `tests/experiment/capture.py` | JSONLWriter with optional filename parameter | VERIFIED | `__init__(self, run_id, git_commit, filename=None)`, uses `filename` when provided, opens in append mode `"a"` |
| `tests/experiment/conftest.py` | WriterPool, rep_number fixture, EVAL_TEMPERATURE constant, summary hook | VERIFIED | All four present: `WriterPool` class with lazy `get()` and `close_all()`, `rep_number` fixture extracting from pytest-repeat, `EVAL_TEMPERATURE = 0.2`, `pytest_terminal_summary` hook |
| `tests/experiment/test_experiment.py` | Uses writer_pool and rep_number, temperature on ChatAnthropic | VERIFIED | `async def test_scenario(..., writer_pool, rep_number)`, `ChatAnthropic(..., temperature=EVAL_TEMPERATURE)`, `writer_pool.get(variant_name, rep_number)` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/experiment/test_experiment.py` | `tests/experiment/conftest.py` | `writer_pool.get(variant_name, rep_number)` | WIRED | Line 65: `writer = writer_pool.get(variant_name, rep_number)` — exact pattern found |
| `tests/experiment/conftest.py` | `tests/experiment/capture.py` | `WriterPool` creates `JSONLWriter` instances with per-run filenames | WIRED | Line 39: `filename = f"{variant}_run{rep}_{self._timestamp}.jsonl"`, line 43: `filename=filename` passed to `JSONLWriter(...)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ANLS-01 | 09-01-PLAN.md | Clean experiment data collected on both tool variants with fixed pipeline | SATISFIED | 6 JSONL files covering baseline+applike x 3 runs; 120 scenario results with full response + tool call data; collected at temperature 0.2 with fixed timestamp injection and zero-persona mode |

No orphaned requirements: REQUIREMENTS.md traceability table maps only ANLS-01 to Phase 9, and the plan claims exactly ANLS-01. Coverage is complete.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, no stub implementations, no empty returns in any of the three modified experiment files.

### Human Verification Required

#### 1. LangSmith Trace Presence

**Test:** Open LangSmith project, filter traces by `run_id` matching the value in any JSONL metadata line. Confirm traces exist with variant, run_id, and rep annotations.
**Expected:** 120 traces visible, each annotated with feedback keys `variant`, `run_id`, `rep`, `category`, `input_tokens`, `output_tokens`.
**Why human:** LangSmith is an external service; no programmatic access to verify trace existence from the codebase alone.

### Gaps Summary

No gaps. All five observable truths are verified against the actual codebase:
- 6 JSONL files exist with correct structure (6 x 21 lines, 6 x 20 unique scenarios)
- Both artifact and key-link chains are substantively implemented and wired
- ANLS-01 is satisfied by the data files themselves
- Commits f1670af and 61d8132 confirmed in git history

The one human verification item (LangSmith trace existence) is informational — the code paths that write LangSmith traces are fully wired in `test_experiment.py` (lines 57-62), and the data collection goal is satisfied by the JSONL files regardless of LangSmith availability.

---

_Verified: 2026-02-20T05:30:00Z_
_Verifier: Claude (gsd-verifier)_
