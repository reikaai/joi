# Phase 5: Full Comparison Exploration

## Overview

This document tracks the iterative exploration of app-like vs programmatic tool interfaces for LLM task scheduling. The approach is two-phase: (1) initial comparison on existing easy scenarios to calibrate, (2) iterative exploration with harder scenarios to find differentiation boundaries. Updated as a living lab notebook after each pivot.

## Phase 4 Reference Data

| Variant | Success Rate | 95% CI | Delta vs Baseline | Avg Cost |
|---------|-------------|--------|-------------------|----------|
| baseline | 95.0% | [86.7%, 98.3%] | -- | $0.003620 |
| rename | 91.7% | [81.7%, 96.7%] | -3.3% | $0.003549 |
| simplify | 91.7% | [81.7%, 96.7%] | -3.3% | $0.003403 |
| description_a | 95.0% | [86.7%, 98.3%] | 0.0% | $0.003658 |
| description_b | 95.0% | [86.7%, 98.3%] | 0.0% | $0.003546 |

All Phase 4 comparisons were not significant. Key finding: isolated tool design changes (renaming, parameter simplification, description rewrites) do not meaningfully affect accuracy at the 95% baseline ceiling.

---

## Pivot 0: Initial Comparison (Existing Scenarios)

**Date:** 2026-02-19
**Config:** applike vs baseline, 12 scenarios (7 positive + 5 negative), 5 reps each = 120 LLM calls
**Model:** claude-haiku-4-5-20251001

### Results

| Variant | Success Rate | 95% CI | n |
|---------|-------------|--------|---|
| baseline | 98.3% | [91.7%, 100.0%] | 60 |
| applike | 93.3% | [84.0%, 98.3%] | 60 |

**Difference:** -5.0% (applike lower)
**Bootstrap CI of difference:** [-11.7%, 0.0%] -- NOT significant (CI upper bound touches zero)

### Fisher Exact Test

| Metric | Value |
|--------|-------|
| p-value | 0.364 |
| Odds ratio | 0.237 |
| Significant | No |

The Fisher exact test confirms no significant difference between the two variants on this scenario set.

### Per-Category Breakdown

| Category | Baseline | Applike | Delta | n per variant |
|----------|----------|---------|-------|---------------|
| single | 100% | 100% | 0% | 5 |
| sequence | 100% | 100% | 0% | 15 |
| recurring | 100% | 100% | 0% | 10 |
| multi | 80% | 40% | -40% | 5 |
| negative | 100% | 96% | -4% | 25 |

The differentiation concentrates in two categories:

1. **multi (two_reminders):** Baseline 80% vs applike 40%. This is the hardest existing scenario -- "remind me in 10 min and again in 20 min" requires two sequential tool calls. With applike, the LLM must decide whether to use `calendar_create_event` (one-time) or `reminders_create` (recurring) for each. This routing decision adds cognitive load that doesn't exist for baseline (where both go to `schedule_task`). However, n=5 is far too small to draw conclusions -- the CIs are [0%, 80%] for applike and [20%, 100%] for baseline.

2. **negative (false triggers):** Baseline 100% vs applike 96%. One false trigger on `neg:past_tense_reminder` ("I forgot to call my mom yesterday, I was supposed to remind myself") -- applike's `calendar_create_event` fired when baseline stayed silent. This suggests the app-like framing ("Calendar" naming) may slightly lower the threshold for triggering on scheduling-adjacent language.

### Cost Comparison

| Variant | Avg Cost/Call | Cost for 60 Calls | vs Baseline |
|---------|---------------|--------------------| ------------|
| baseline | $0.003676 | $0.221 | -- |
| applike | $0.003637 | $0.218 | -1.1% |

Cost difference is negligible. Applike is marginally cheaper despite richer tool descriptions, likely because shorter output tokens (app-like names vs longer parameter names) offset longer input tokens.

### Additive Null Model

Phase 4 isolated deltas:
- rename: -3.3%
- simplify: -3.3%
- description: 0.0%

**Expected under additive model:** 95.0% - 3.3% - 3.3% - 0.0% = 88.4%
**Actual applike (Phase 5):** 93.3%
**Phase 5 baseline (for comparison):** 98.3%

Interpretation: Applike at 93.3% BEATS the additive prediction of 88.4% by +4.9 percentage points. This suggests a small positive synergy -- the coherent "Calendar/Reminders" framing partially compensates for the structural changes. However, the Phase 5 baseline also shifted up to 98.3% (from 95.0% in Phase 4), making the raw delta -5.0% rather than -1.7%. All within CI noise -- the additive model is directionally right but the variance is too high for precise decomposition.

Note: the baseline shift (95.0% -> 98.3%) is within the Phase 4 CI [86.7%, 98.3%] and reflects normal LLM sampling variance, not a systematic change.

### Observation

As expected, no significant difference at the 95%+ ceiling. The per-category breakdown reveals that the `multi:two_reminders` scenario is the only one where applike consistently underperforms, but the sample size (n=5 per variant) is too small to be conclusive. The core single/sequence/recurring categories show identical 100% performance for both variants.

The applike variant's main risk is multi-tool routing: when a request could go to either `calendar_create_event` or `reminders_create`, the LLM sometimes hesitates or refuses entirely. Baseline doesn't have this problem because everything goes through `schedule_task`.

### Next

Proceed to hard scenario design. Three priorities:
1. **Multi-tool routing stress tests** -- the one area where applike might genuinely differ
2. **Ambiguous intent scenarios** -- test whether app-like naming helps/hurts intent recognition
3. **Lower the baseline** -- current scenarios are too easy (98%+ ceiling). Need to push baseline to 60-70% for meaningful statistical power
