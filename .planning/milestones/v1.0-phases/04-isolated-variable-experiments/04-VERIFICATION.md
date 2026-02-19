---
phase: 04-isolated-variable-experiments
verified: 2026-02-19T17:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 4: Isolated Variable Experiments Verification Report

**Phase Goal:** Interpretable signal on which individual variable (naming, parameter simplification, description style) drives tool-use improvement
**Verified:** 2026-02-19T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Rename-only variant has been compared to baseline with bootstrap confidence intervals reported | VERIFIED | `latest.json`: rename vs baseline diff=-3.3%, CI=[-13.3%, +5.0%], significant=False |
| 2  | Simplify-only variant has been compared to baseline with bootstrap confidence intervals reported | VERIFIED | `latest.json`: simplify vs baseline diff=-3.3%, CI=[-11.7%, +3.3%], significant=False |
| 3  | Description-only variant has been compared to baseline with bootstrap confidence intervals reported | VERIFIED | `latest.json`: description_a and description_b vs baseline, both CI=[-6.7%, +6.7%] |
| 4  | Each comparison has sufficient sample size for interpretable results (minimum 3 repeat runs per scenario) | VERIFIED | All 5 variants have n=60 (12 scenarios x 5 reps). Minimum required was 3 reps. |
| 5  | Results clearly show which variable(s) produce statistically significant improvement (or show no significant difference) | VERIFIED | `phase4_summary.md` section 4 interprets each comparison explicitly; all 4 show "No" in Significant? column with narrative verdicts |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/eval/reports/latest.json` | Raw JSON report with per-variant CIs and pairwise comparisons | VERIFIED | Exists; 5 variants, 10 comparisons, `comparisons` key present, BCa CI bounds present for all variants |
| `tests/eval/reports/phase4_summary.md` | Human-readable markdown summary table for Phase 5 consumption | VERIFIED | Exists; 7 sections, contains `significant` keyword 5 times, per-comparison interpretation paragraphs present |
| `tests/eval/evaluators.py` | Fixed evaluate_tool_calls with multi-tool support, _check_staggered_timing without hardcoded names | VERIFIED | `schedule_tool_names` present at line 109; `_check_staggered_timing` uses delay_seconds/int-when/string-when tiers with no hardcoded tool name gates |
| `tests/eval/test_tasks.py` | Fixed test_negative with multi-tool filtering | VERIFIED | `schedule_tool_names` present at line 148; test_negative uses the same fallback pattern |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/eval/evaluators.py` | `tests/eval/variants/registry.py` | `variant.schedule_tool_names` field | VERIFIED | Line 109: `schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]` |
| `tests/eval/test_tasks.py` | `tests/eval/variants/registry.py` | `variant.schedule_tool_names` field | VERIFIED | Line 148: same pattern applied in test_negative |
| `tests/eval/reports/phase4_summary.md` | `tests/eval/reports/latest.json` | Derived from JSON report data | VERIFIED | All numbers in summary match JSON exactly (95.0%, 91.7%, CIs); footer cites source file |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| EXPR-02 | 04-01-PLAN.md, 04-02-PLAN.md | Run isolated variable experiments (rename-only, simplify-only, description-only) | SATISFIED | 300 LLM calls across 5 variants with bootstrap CIs; all 4 isolated comparisons vs baseline documented in `latest.json` and `phase4_summary.md` |

**Orphaned requirements check:** REQUIREMENTS.md maps only EXPR-02 to Phase 4. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/eval/evaluators.py` | 66, 80 | `sname == "do_later"` | Info | Hardcoded name in `_check_has_timing` and `_check_is_recurring` — NOT in `_check_staggered_timing`. These two functions have different semantics that depend on tool arg structure; the plan's fix target was `_check_staggered_timing` only. Not a blocker. |

No blocker or warning anti-patterns. The residual `do_later` references are in `_check_has_timing` and `_check_is_recurring` (not `_check_staggered_timing`), and they handle genuine structural differences in how the simplify variant encodes timing, not hardcoded filtering bugs.

### Human Verification Required

None. All success criteria are programmatically verifiable via the JSON report and markdown summary.

### Gaps Summary

No gaps. All five success criteria from ROADMAP.md are satisfied with direct evidence in the codebase:

- `tests/eval/reports/latest.json` contains all 5 variants with n=60 each, 10 pairwise comparisons with bootstrap BCa 95% CIs, and `significant` flags.
- `tests/eval/reports/phase4_summary.md` contains per-variant result table, 4 baseline comparison rows with explicit `Significant?` column and interpretation paragraphs, description A vs B head-to-head, token cost analysis, and a 3-bullet key findings section.
- The evaluator fixes are substantive and wired: `schedule_tool_names` fallback pattern is used in both `evaluators.py` and `test_tasks.py`; `_check_staggered_timing` contains no hardcoded tool name gates.
- Commits 67d6213, 3b2e6e1, and c9415b4 all verified present in git history.
- `ruff check` passes on both modified files.

---

_Verified: 2026-02-19T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
