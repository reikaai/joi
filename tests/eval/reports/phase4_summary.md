# Phase 4: Isolated Variable Experiment Results

## 1. Experiment Metadata

| Field | Value |
|-------|-------|
| Date | 2026-02-19 |
| Model | claude-haiku-4-5-20251001 |
| Repetitions | 5 per scenario per variant |
| Scenarios | 12 (7 positive + 5 negative) |
| Variants tested | 5 (baseline, rename, simplify, description_a, description_b) |
| Total LLM calls | 300 |
| Total tokens | 854,902 |
| Total cost | $1.07 |
| Statistical method | Bootstrap BCa 95% CI (n_resamples=9999, seed=42) |

## 2. Per-Variant Results

| Variant | N | Success Rate | CI (95%) | Avg Tokens | Avg Cost |
|---------|---|--------------|----------|------------|----------|
| baseline | 60 | 95.0% | [86.7%, 98.3%] | 2886 | $0.003620 |
| description_a | 60 | 95.0% | [86.7%, 98.3%] | 2986 | $0.003658 |
| description_b | 60 | 95.0% | [86.7%, 98.3%] | 2795 | $0.003546 |
| rename | 60 | 91.7% | [81.7%, 96.7%] | 2826 | $0.003549 |
| simplify | 60 | 91.7% | [81.7%, 96.7%] | 2756 | $0.003403 |

## 3. Baseline Comparisons

| Variant vs Baseline | Difference | CI (95%) | Significant? | Interpretation |
|---------------------|------------|----------|--------------|----------------|
| description_a vs baseline | +0.0% | [-6.7%, +6.7%] | No | No meaningful effect detected (narrow CI, symmetric around zero) |
| description_b vs baseline | +0.0% | [-6.7%, +6.7%] | No | No meaningful effect detected (narrow CI, symmetric around zero) |
| rename vs baseline | -3.3% | [-13.3%, +5.0%] | No | No detectable effect (CI includes zero; wider spread suggests more variance) |
| simplify vs baseline | -3.3% | [-11.7%, +3.3%] | No | No detectable effect (CI includes zero; slight negative lean but not significant) |

## 4. Interpretation of Each Comparison

### description_a vs baseline
- **Difference:** 0.0% (identical means)
- **CI:** [-6.7%, +6.7%] -- narrow and symmetric
- **Verdict:** Rewriting tool descriptions with emphasis on purpose/context has no measurable effect on tool selection accuracy. The CI is narrow enough to rule out effects larger than ~7%.

### description_b vs baseline
- **Difference:** 0.0% (identical means)
- **CI:** [-6.7%, +6.7%] -- narrow and symmetric
- **Verdict:** Alternative description rewrite also has no measurable effect. Both description variants produce results indistinguishable from baseline.

### rename vs baseline
- **Difference:** -3.3% (rename slightly worse)
- **CI:** [-13.3%, +5.0%] -- wider, asymmetric toward negative
- **Verdict:** Renaming tools (e.g., schedule_task -> calendar_create_event) shows a slight negative trend but the effect is not statistically significant. The wider CI (-13.3% to +5.0%) suggests renaming introduces more variance in LLM behavior. Cannot rule out effects up to -13.3%.

### simplify vs baseline
- **Difference:** -3.3% (simplify slightly worse)
- **CI:** [-11.7%, +3.3%] -- leans negative
- **Verdict:** Simplifying tool parameters (merging timing params into typed `when`) shows a slight negative trend. Not significant, but the CI upper bound is only +3.3%, suggesting the effect is unlikely to be positive. The simplification may make the tool slightly harder for the LLM to use correctly.

## 5. Description A vs B (Head-to-Head)

| Comparison | Difference | CI (95%) | Significant? |
|------------|------------|----------|--------------|
| description_a vs description_b | +0.0% | [-6.7%, +6.7%] | No |

**Interpretation:** The two description rewrite strategies produce identical success rates (95.0% each). There is no detectable difference between a purpose-focused rewrite (A) and an alternative rewrite (B). Both are equivalent to baseline, and equivalent to each other.

## 6. Token Cost Analysis

| Variant | Avg Tokens | vs Baseline | Avg Cost | vs Baseline |
|---------|------------|-------------|----------|-------------|
| baseline | 2886 | -- | $0.003620 | -- |
| description_a | 2986 | +100 (+3.5%) | $0.003658 | +$0.000038 (+1.0%) |
| description_b | 2795 | -91 (-3.2%) | $0.003546 | -$0.000074 (-2.0%) |
| rename | 2826 | -60 (-2.1%) | $0.003549 | -$0.000071 (-2.0%) |
| simplify | 2756 | -130 (-4.5%) | $0.003403 | -$0.000217 (-6.0%) |

**Observations:**
- **simplify** is the cheapest variant (-6.0% cost vs baseline), likely due to fewer/simpler tool parameters reducing output tokens
- **description_a** is slightly more expensive (+1.0%) -- longer descriptions cost slightly more in input tokens
- **description_b** and **rename** are ~2% cheaper than baseline
- Cost differences are small in absolute terms ($0.0002/call max)

## 7. Key Findings for Phase 5

1. **No isolated variable produces a statistically significant improvement.** All 4 baseline comparisons have CIs that include zero. The hypothesis that individual tool design changes (naming, parameter simplification, description rewrites) meaningfully affect LLM tool selection accuracy is not supported at n=60.

2. **Baseline is already strong (95.0%).** With a 95% success rate, there is limited room for improvement. The ceiling effect may mask small genuine effects -- a harder scenario set would be needed to differentiate variants.

3. **Rename and simplify show a (non-significant) negative trend (-3.3%).** While not statistically significant, both structural changes (renaming tools, simplifying params) lean negative. This suggests that changing tool structure -- even with "cleaner" designs -- may introduce LLM confusion compared to familiar patterns. Phase 5 should test whether combining these changes (as in the applike variant) amplifies this trend or whether the app-like framing compensates.

---

*Generated from `tests/eval/reports/latest.json` on 2026-02-19*
*Statistical method: Bootstrap BCa 95% CI, n_resamples=9999, seed=42*
