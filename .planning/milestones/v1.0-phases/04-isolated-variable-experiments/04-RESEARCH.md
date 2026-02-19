# Phase 4: Isolated Variable Experiments - Research

**Researched:** 2026-02-19
**Domain:** Running controlled LLM tool-use experiments, statistical analysis of isolated variables, pytest-repeat execution
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPR-02 | Run isolated variable experiments (rename-only, simplify-only, description-only) | All infrastructure exists (eval framework from Phase 2, variants from Phase 3). Primary work is: executing experiments with sufficient repetitions, fixing evaluator gaps for multi-tool variants, collecting results, computing bootstrap CIs, and generating a comparison report. |
</phase_requirements>

## Summary

Phase 4 is an execution and analysis phase, not a building phase. All infrastructure (eval framework, variants, scenarios, statistics) was built in Phases 2-3. The primary work is: (1) fixing evaluator gaps that would cause incorrect results for non-baseline variants, (2) running the eval suite with sufficient repetitions (minimum 5 runs per scenario per variant), (3) collecting and analyzing results using the existing bootstrap CI infrastructure, and (4) generating a clear comparison report.

The most critical finding from this research is that **the existing evaluator has bugs that will produce incorrect results for non-baseline variants**. Specifically: (a) the evaluator only checks `schedule_tool_name` (singular) for the applike variant, missing `reminders_create` calls entirely, (b) the staggered_timing assertion hardcodes tool name checks that don't cover renamed variants, and (c) the `paired=True` bootstrap comparison assumes array alignment by scenario, which is fragile. These must be fixed BEFORE running experiments or the results will be uninterpretable.

**Primary recommendation:** Fix the evaluator bugs first (small, focused changes), then run 5 isolated experiments (baseline, rename, simplify, description_a, description_b) with `--count=5` for statistical power, generate the report, and interpret results. Exclude the applike variant from Phase 4 (it's Phase 5's subject).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.4 (installed) | Test runner | Already configured with eval marker |
| pytest-repeat | >=0.9.4 (installed) | `--count=N` for repeated test execution | Standard approach for LLM eval statistical sampling |
| scipy | >=1.14 (installed) | Bootstrap BCa confidence intervals | Already wired in `stats.py` |
| langchain-anthropic | >=1.3.1 (installed) | ChatAnthropic for LLM calls | Already used in `test_tasks.py` |
| langsmith | >=0.6.8 (installed) | Experiment tracking via `@pytest.mark.langsmith` | Already wired |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (scipy dep, installed) | Array operations for bootstrap | Used internally by `stats.py` |
| pyyaml | (installed) | Scenario YAML loading | Already used by `conftest.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-repeat `--count=5` | Multiple manual `uv run pytest` invocations | pytest-repeat gives N samples per parametrize combo in a single session; manual runs require merging results across sessions |
| Single-session all-variants run | Per-variant separate runs | Single session ensures paired bootstrap comparison works (same scenario order). Separate runs break `paired=True`. |

**Installation:** No new dependencies required. Everything is already installed.

## Architecture Patterns

### Recommended Experiment Structure
```
tests/
├── eval/
│   ├── test_tasks.py          # Existing: parametrized tests (needs variant filtering)
│   ├── conftest.py            # Existing: results collection + report generation
│   ├── evaluators.py          # Existing: NEEDS FIXES for non-baseline variants
│   ├── stats.py               # Existing: bootstrap CI + report (needs scenario alignment)
│   ├── variants/              # All 6 variants (run 5 for Phase 4)
│   ├── scenarios/             # 7 positive + 5 negative YAML scenarios
│   ├── cache/                 # Per-variant/per-scenario JSON cache
│   └── reports/
│       └── latest.json        # Generated after each run
```

### Pattern 1: Running Isolated Experiments
**What:** Run specific variants against baseline using pytest -k filtering.
**When to use:** Phase 4 experiments.
**Example:**
```bash
# Run baseline + all 4 isolated variants (NOT applike), 5 repetitions each
uv run pytest -m eval --count=5 \
  -k "baseline or rename or simplify or description_a or description_b" \
  -v

# Cost: 12 scenarios * 5 variants * 5 reps = 300 LLM calls
# At ~$0.003/call = ~$0.90 total
```

### Pattern 2: Variant-Specific Comparison
**What:** The `generate_report` function automatically computes pairwise comparisons. For Phase 4, the relevant comparisons are each isolated variant vs baseline.
**When to use:** Interpreting results.
**Example output from `reports/latest.json`:**
```json
{
  "variants": {
    "baseline": {"n_samples": 60, "success_rate": {"mean": 0.92, "ci_low": 0.85, "ci_high": 0.97}},
    "rename": {"n_samples": 60, "success_rate": {"mean": 0.95, "ci_low": 0.88, "ci_high": 0.99}}
  },
  "comparisons": [
    {
      "variant_a": "baseline", "variant_b": "rename",
      "difference": -0.03, "ci_low": -0.08, "ci_high": 0.02,
      "significant": false
    }
  ]
}
```

### Pattern 3: Paired Bootstrap for Scenario-Aligned Comparison
**What:** The existing `compare_variants(paired=True)` requires that both score arrays are aligned by scenario. This means a_scores[i] and b_scores[i] must correspond to the same scenario.
**When to use:** All pairwise comparisons.
**Critical requirement:** Results must be collected in the same order for all variants within a single pytest session. The current parametrize order guarantees this IF all variants run in the same session.

### Anti-Patterns to Avoid
- **Running variants in separate sessions:** Breaks paired bootstrap alignment. Results from different sessions may have different scenario orderings or cached states. Always run compared variants in a single session.
- **Using `--count=3` (the bare minimum):** BCa bootstrap with 3 samples per scenario produces very wide CIs. 5 repetitions is the practical minimum; 10 is better for tight CIs.
- **Running the applike variant in Phase 4:** Applike is a multi-dimensional change. Phase 4 is about isolated variables. Including it creates noise in comparisons and wastes LLM budget.
- **Interpreting negative scenarios independently from positive:** Negative scenarios (no false triggers) should be reported separately. A variant that improves positive accuracy but increases false positive rate is worse, not better.
- **Ignoring token cost in the comparison:** Two variants with similar accuracy but different token costs are NOT equivalent. Report token costs alongside accuracy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Repeated test execution | Custom loop in test code | `pytest-repeat --count=5` | Clean parametrization, proper test isolation, compatible with LangSmith tracking |
| Statistical comparison | Manual mean comparison | `stats.compare_variants()` (already built) | Handles edge cases, BCa correction, significance check |
| Report generation | Manual log parsing | `conftest._generate_report_on_finish` (already built) | Autouse session fixture, writes JSON automatically |
| LLM response caching | External cache layer | Built-in JSON cache in `test_tasks.py` | Already implemented, per-variant/per-scenario granularity |

**Key insight:** Phase 4 is 90% execution and 10% fixing. The infrastructure exists. The work is: fix evaluator bugs, run the experiment, interpret results.

## Common Pitfalls

### Pitfall 1: Evaluator Bugs for Non-Baseline Variants
**What goes wrong:** The evaluator produces incorrect scores for renamed variants.
**Why it happens:** Three specific issues:
1. `evaluate_tool_calls()` filters schedule calls using `variant.schedule_tool_name` (singular). For the applike variant with `schedule_tool_names=["calendar_create_event", "reminders_create"]`, recurring scenarios where the LLM correctly calls `reminders_create` will score 0 because the evaluator only checks `calendar_create_event`.
2. `_check_staggered_timing()` hardcodes `sname in ("schedule_task", "tasks")` at line 39 and `sname in ("schedule_task", "do_later")` at line 49. The rename variant uses `calendar_create_event` which matches NEITHER branch, so staggered timing is never checked.
3. `_check_has_timing()` has `sname == "do_later"` at line 70 as a special case, but the generic else path works for any tool. This one is OK for rename.
**How to avoid:** Fix the evaluator before running experiments:
- In `evaluate_tool_calls()`: use `schedule_tool_names` (plural) if set, falling back to `[schedule_tool_name]`. Filter calls matching ANY name in the list.
- In `_check_staggered_timing()`: remove the hardcoded name checks. Use `variant.schedule_tool_name` or just check for `delay_seconds` / `when` presence in args regardless of tool name.
- These are small, targeted fixes (< 20 lines changed).
**Warning signs:** Rename variant showing 0% accuracy on sequence scenarios; applike variant showing 0% on recurring scenarios.

### Pitfall 2: Paired Bootstrap With Unequal Sample Counts
**What goes wrong:** `compare_variants(paired=True)` requires both arrays to have the same length. If one variant fails to produce results for some scenarios (e.g., evaluator crash), the arrays are misaligned.
**Why it happens:** `eval_results[variant_name].append(...)` collects results in test execution order. If a test for one variant raises an unexpected exception (not an assertion failure), its result is not recorded, causing array length mismatch.
**How to avoid:** The `record_eval_result` call happens BEFORE the assert in `test_positive` and `test_negative`, so even failing assertions still record the result. The risk is only from unexpected exceptions (LLM call failure, import error). Use `LANGSMITH_TEST_CACHE=write` on first run to populate cache, then `LANGSMITH_TEST_CACHE=read` for reliable repeat runs.
**Warning signs:** `compare_variants` returning `warning: "Too few samples"` or NaN CIs.

### Pitfall 3: Cache Invalidation Between Repeat Runs
**What goes wrong:** With `--count=5`, all 5 repetitions hit the same cache file and get the same response. This makes all 5 "runs" identical -- zero variance, no meaningful CI.
**Why it happens:** The cache key is `{variant_name}/{scenario_id}.json`. It doesn't include a repetition index. Repeat runs return the cached response from run 1.
**How to avoid:** For the experiment, DO NOT use cache mode. Run with `LANGSMITH_TEST_CACHE=""` (empty/unset) to make real LLM calls every time. Cache is for regression/development, not for statistical sampling. Alternatively, if cost is a concern, run `--count=1` with `LANGSMITH_TEST_CACHE=write` to populate cache, then run subsequent counts with real calls (no cache).
**Warning signs:** All 5 runs producing identical scores per scenario; bootstrap CI with std_error=0.0.

### Pitfall 4: LangSmith Free Tier Trace Budget
**What goes wrong:** 300 LLM calls * 5 test functions = potential trace budget exhaustion.
**Why it happens:** Each pytest test case with `@pytest.mark.langsmith` creates a LangSmith trace. With 5 variants * 12 scenarios * 5 reps = 300 traces. The free tier allows 5,000/month.
**How to avoid:** 300 traces is well within the 5,000 monthly limit. But if running multiple experiments or debugging, consider using `LANGSMITH_TEST_TRACKING=false` for dry runs. Only enable tracking for the final official experiment run.
**Warning signs:** HTTP 429 from LangSmith API.

### Pitfall 5: Interpreting Non-Significant Results as "No Effect"
**What goes wrong:** Reporting "rename has no significant effect" when the CI is [-0.15, +0.20]. This wide CI means we can't distinguish between a 15% decrease and a 20% increase -- the sample size was too small.
**Why it happens:** With 12 scenarios * 5 reps = 60 data points per variant for binary outcomes, CIs will be moderate. Not all comparisons will be "significant."
**How to avoid:** Report CIs with interpretation. A non-significant result with a NARROW CI around zero ("CI: [-0.02, +0.03]") means "genuinely no effect." A non-significant result with a WIDE CI ("CI: [-0.15, +0.20]") means "insufficient power to detect an effect." These are different conclusions.
**Warning signs:** Wide CIs with >10% spread; drawing conclusions from non-significant results without noting CI width.

### Pitfall 6: Simplify Variant Evaluator Incompatibility
**What goes wrong:** The simplify variant uses `when: int | str` instead of `delay_seconds`. The `_check_staggered_timing` function checks for `delays = [tc["args"].get("delay_seconds")]` which will be None for simplify variant.
**Why it happens:** The simplify variant merges delay_seconds into `when` as an integer. The evaluator was written for the baseline's parameter structure.
**How to avoid:** The existing code at lines 49-55 of evaluators.py handles `int_whens` for `schedule_task` tool name. Since simplify still uses `schedule_task` as its tool name, this path should work. But verify with a dry run: `--count=1 -k "simplify and seq:count3"`.
**Warning signs:** All staggered_timing assertions failing for simplify variant.

## Code Examples

### Fix 1: Evaluator Multi-Tool Support
```python
# evaluators.py: evaluate_tool_calls() -- fix schedule call filtering
def evaluate_tool_calls(response, scenario: Scenario, variant: ToolVariant) -> EvalResult:
    result = EvalResult()
    all_tool_calls = response.tool_calls

    # Use schedule_tool_names (plural) if set, else singleton list
    schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]
    schedule_calls = [tc for tc in all_tool_calls if tc["name"] in schedule_names]

    if variant.schedule_action:
        schedule_calls = [c for c in schedule_calls if c["args"].get("action") == variant.schedule_action]
    # ... rest unchanged
```

### Fix 2: Evaluator Staggered Timing for Any Tool Name
```python
# evaluators.py: _check_staggered_timing() -- remove hardcoded tool names
def _check_staggered_timing(calls: list[dict], variant: ToolVariant) -> str | None:
    # Check for delay_seconds (baseline, rename, description_a/b)
    delays = [tc["args"].get("delay_seconds") for tc in calls]
    if any(d is not None for d in delays):
        if not all(d is not None for d in delays):
            return f"Mixed delay_seconds presence. delays={delays}"
        if delays != sorted(delays) or len(set(delays)) != len(delays):
            return f"delay_seconds not strictly increasing. delays={delays}"
        return None

    # Check for int-valued when (simplify variant, applike)
    whens = [tc["args"].get("when", "") for tc in calls]
    int_whens = [w for w in whens if isinstance(w, int)]
    if len(int_whens) == len(calls) and len(calls) > 1:
        if int_whens != sorted(int_whens) or len(set(int_whens)) != len(int_whens):
            return f"int when values not strictly increasing. whens={int_whens}"
        return None

    # String when values: just verify distinct
    unique = len(set(str(w) for w in whens if w != "" and w is not None))
    if unique < 2:
        return f"Sequence calls should have distinct timing. whens={whens}"

    return None
```

### Fix 3: Negative Test Multi-Tool Support
```python
# test_tasks.py: test_negative() -- fix schedule call filtering
async def test_negative(variant_name: str, scenario: Scenario, eval_results: dict):
    variant = VARIANTS[variant_name]
    # ...
    schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]
    schedule_calls = [tc for tc in response.tool_calls if tc["name"] in schedule_names]
    # ... rest unchanged
```

### Running the Experiment
```bash
# Phase 4: Run 5 isolated variants with 5 repetitions (no cache for fresh LLM responses)
uv run pytest -m eval --count=5 \
  -k "baseline or rename or simplify or description_a or description_b" \
  -v --tb=short 2>&1 | tee eval_results_phase4.txt

# Report is auto-generated at tests/eval/reports/latest.json
# View summary:
cat tests/eval/reports/latest.json | python -m json.tool
```

### Interpreting Results
```python
# After run, the report contains:
# 1. Per-variant success rates with CIs
# 2. Pairwise comparisons with significance flags
# Focus on these 4 comparisons:
#   - baseline vs rename
#   - baseline vs simplify
#   - baseline vs description_a
#   - baseline vs description_b
#
# For each, check:
# - Is the difference significant? (significant: true/false)
# - What direction? (positive = variant better than baseline)
# - How wide is the CI? (narrow = confident, wide = need more data)
# - Token cost delta? (cheaper variant at same accuracy = clear winner)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-run pass/fail eval | Multi-run statistical eval with CIs | This project (Phase 2) | Reproducible, interpretable results |
| Manual variant comparison | Automated pairwise bootstrap comparison | This project (Phase 2) | Scales to N variants |
| Custom eval caching | JSON file cache with write/read modes | This project (Phase 2) | Cheap regression runs |

**Deprecated/outdated:**
- Running eval once and drawing conclusions: LLM outputs are stochastic; need multiple samples
- Using p-values for small LLM eval samples: Bootstrap CIs are more appropriate and interpretable

## Open Questions

1. **Number of repetitions: 5 vs 10**
   - What we know: `--count=5` gives 60 data points per variant (12 scenarios * 5 reps). BCa bootstrap with 60 binary samples produces moderate CIs. 10 reps gives 120 data points and tighter CIs but costs ~$1.80 vs $0.90.
   - What's unclear: Whether 5 reps provides sufficient power to detect a 10% accuracy improvement.
   - Recommendation: Start with 5. If CIs are too wide (>10% spread) for any comparison, re-run with 10. The cost difference is negligible.

2. **Scenario alignment for paired bootstrap**
   - What we know: `compare_variants(paired=True)` requires aligned arrays. The current code appends results in test execution order. Pytest parametrize order is deterministic within a session.
   - What's unclear: With `--count=5`, does pytest-repeat interleave repetitions (AABBCC) or group them (AAABBB)?
   - Recommendation: Verify by running `--count=2 --collect-only` and checking the test order. If repetitions are grouped rather than interleaved, the arrays won't be scenario-aligned. In that case, either (a) sort results by scenario_id before comparison, or (b) switch to `paired=False` (independent bootstrap, slightly less power but no alignment requirement).

3. **Should description_a and description_b be compared to each other?**
   - What we know: Phase 4 success criteria say "description-only variant has been compared to baseline." There are TWO description variants.
   - What's unclear: Whether comparing description_a vs description_b against each other (not just vs baseline) adds value.
   - Recommendation: Yes, compare both vs baseline AND vs each other. The a-vs-b comparison answers "does structured description outperform minimal?" which is directly actionable for future tool design. The report already computes all pairwise comparisons, so this comes free.

4. **How to present results for Phase 5 consumption**
   - What we know: Phase 5 needs "isolated results to interpret combined results." The report JSON has all raw data.
   - What's unclear: Whether a human-readable summary (markdown) is needed alongside the JSON report.
   - Recommendation: Generate a markdown summary in addition to JSON. The markdown should have a table: variant | success_rate | CI | vs_baseline_diff | significant? | token_cost. This makes Phase 5 consumption trivial.

5. **Evaluator fixes: should they be committed before or as part of Phase 4?**
   - What we know: The evaluator bugs affect non-baseline variants. Phase 3 never ran experiments, so the bugs were not caught.
   - What's unclear: Whether fixing evaluator bugs counts as Phase 4 work or is a Phase 2/3 debt.
   - Recommendation: Fix as part of Phase 4 since the bugs only manifest during experiment execution. The fixes are small (< 20 lines) and don't change the framework architecture.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `tests/eval/evaluators.py` (line-by-line analysis of assertion logic) -- identified 2 hardcoded tool name bugs
- Existing codebase: `tests/eval/test_tasks.py` -- verified cache implementation and repeat behavior
- Existing codebase: `tests/eval/stats.py` -- confirmed `paired=True` requirement and edge case handling
- Existing codebase: `tests/eval/variants/registry.py` -- confirmed `schedule_tool_names` field exists but is unused by evaluator
- Existing codebase: All 6 variant files verified -- confirmed tool name mappings and parameter structures
- [scipy.stats.bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) -- BCa method, `paired` parameter behavior, degenerate distribution handling
- [pytest-repeat documentation](https://pypi.org/project/pytest-repeat/) -- `--count` parameter, `--repeat-scope` for controlling repetition granularity

### Secondary (MEDIUM confidence)
- [Bootstrap confidence intervals tutorial](https://acclab.github.io/bootstrap-confidence-intervals.html) -- general guidelines for BCa sample sizes
- Efron & Tibshirani rule of thumb: minimum 30 samples for bootstrap, 50-60 for standard errors (widely cited in statistics literature)
- LangSmith free tier: 5,000 traces/month, verified from Phase 2 research

### Tertiary (LOW confidence)
- Cost estimate: ~$0.003 per Haiku 4.5 call with 3-4 tools bound (based on Phase 2 research, not measured for Phase 4 variants specifically)
- pytest-repeat interleaving behavior: assumed deterministic within session but not verified with `--count` > 1

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and proven in Phases 2-3; no new dependencies
- Architecture: HIGH -- Infrastructure exists; only execution and small fixes needed
- Pitfalls: HIGH -- Evaluator bugs identified through direct line-by-line code analysis; cache behavior verified from implementation
- Statistical approach: HIGH -- scipy bootstrap BCa is proven; `compare_variants()` already handles edge cases
- Cost estimate: MEDIUM -- Based on Phase 2 research, not measured with current variant set

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable infrastructure; no external dependency changes expected)
