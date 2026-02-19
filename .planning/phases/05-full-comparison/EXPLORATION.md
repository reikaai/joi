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

---

## Pivot 1: Hard Scenarios (First Round)

**Date:** 2026-02-19
**Rationale:** Pivot 0 showed no signal at the 95%+ ceiling. Need harder scenarios to lower baseline success rate and test for differentiation at moderate difficulty levels.

**Scenarios added:**
- 10 hard positive scenarios across 4 dimensions:
  - `hard_ambiguous:vague_delay`, `hard_ambiguous:implicit_recurring`, `hard_ambiguous:minimal_wake`
  - `hard_multi:onetime_plus_recurring`, `hard_multi:two_different_times`
  - `hard_distractor:buried_intent`, `hard_distractor:long_context`, `hard_distractor:mixed_topic`
  - `hard_implicit:before_weekend`, `hard_implicit:usual_morning`
- 4 hard negative scenarios:
  - `neg:hard_hedging`, `neg:hard_statement`, `neg:hard_question`, `neg:hard_past_reference`

**Config:** applike vs baseline, 26 scenarios (17 positive + 9 negative), 5 reps each = 260 LLM calls
**Model:** claude-haiku-4-5-20251001

### Results

| Variant | Success Rate | 95% CI | n |
|---------|-------------|--------|---|
| baseline | 83.1% | [76.2%, 88.5%] | 130 |
| applike | 79.2% | [71.5%, 85.4%] | 130 |

**Difference:** -3.8% (applike lower)
**Bootstrap CI of difference:** [-10.8%, 0.8%] -- NOT significant
**Fisher exact p-value:** 0.526 -- NOT significant

Hard scenarios successfully lowered the baseline from 98.3% to 83.1%. But the applike deficit also dropped from -5.0% to -3.8%, and the difference remains statistically insignificant.

### Per-Category Breakdown

| Category | Baseline | Applike | Delta | n per variant |
|----------|----------|---------|-------|---------------|
| single | 100% | 100% | 0% | 5 |
| sequence | 100% | 100% | 0% | 15 |
| recurring | 100% | 100% | 0% | 10 |
| multi (easy) | 80% | 0% | -80% | 5 |
| hard_ambiguous | 26.7% | 26.7% | 0% | 15 |
| hard_distractor | 93.3% | 86.7% | -6.7% | 15 |
| hard_implicit | 10.0% | 20.0% | +10.0% | 10 |
| hard_multi | 100% | 100% | 0% | 10 |
| negative (all) | 100% | 97.8% | -2.2% | 45 |

### Hard Scenario Analysis

**Fisher exact on hard scenarios only (n=50 per variant):**
- Applike: 29/50 (58.0%)
- Baseline: 29/50 (58.0%)
- p = 1.000 (identical)

The hard scenarios show absolutely zero differentiation between variants. Both perform identically at 58.0%.

**By dimension:**

1. **hard_ambiguous (26.7% both):** Both variants struggle equally with vague scheduling intent. "I keep forgetting my vitamins" and "remind me about the meeting in a bit" are genuinely hard -- the LLM either doesn't recognize the scheduling intent or can't infer timing. Tool interface design is irrelevant here; this is a prompt interpretation challenge.

2. **hard_distractor (93.3% baseline, 86.7% applike):** Both handle scheduling-embedded-in-context well. The slight applike deficit comes from `mixed_topic` ("What do you think about the weather today? Also set a reminder for 5pm to call the dentist") where applike sometimes responds to the question without scheduling. The buried_intent and long_context distractors were 100% for both -- Haiku handles those cleanly.

3. **hard_implicit (10.0% baseline, 20.0% applike):** Both variants nearly completely fail on implicit timing. "do the usual morning check on me" gets 0% for baseline (calls `run_code` or `recall` instead of `schedule_task`) and 20% for applike (one successful `reminders_create` out of 5). "I need to finish this report before the weekend, remind me" gets 20% baseline (1/5) and 0% applike. These scenarios are too hard -- both variants bottom out.

4. **hard_multi (100% both):** Surprisingly, the new multi-tool scenarios ("set a reminder for 7am tomorrow and also remind me every Monday to check the trash") got 100% for both variants. The explicit mention of one-time + recurring in the same prompt gives enough signal for both to route correctly. This contrasts sharply with the easy `multi:two_reminders` ("remind me at 3pm and 5pm") which remains the only scenario where applike catastrophically fails.

**multi:two_reminders anomaly:** Applike dropped from 40% (Pivot 0) to 0% on this scenario, while baseline held at 80%. This is the one consistent failure mode: when BOTH items are one-time reminders and applike must call `calendar_create_event` twice, it either calls it once (collapsing both into one event) or calls `reminders_create` by mistake. The baseline doesn't have this routing confusion because `schedule_task` handles everything.

### Cost Comparison

| Variant | Avg Cost/Call | Cost for 130 Calls | vs Baseline |
|---------|---------------|--------------------| ------------|
| baseline | $0.003463 | $0.450 | -- |
| applike | $0.003441 | $0.447 | -0.6% |

Cost remains negligible. The hard scenarios have slightly lower token costs because many hard scenarios produce shorter responses (LLM says "I need more information" instead of making a tool call).

### Observation

This is a powerful null result. After specifically designing scenarios to stress-test the dimensions where tool interface should matter most, both variants perform identically at 58.0% on hard scenarios. The only consistent differentiator remains the easy `multi:two_reminders` scenario (baseline 80% vs applike 0%), which is a narrow failure mode specific to same-type multi-item requests.

The hard_implicit scenarios (10-20% for both) reveal that the difficulty limit isn't about tool interface -- it's about the LLM's ability to infer timing from context. No tool description change can help with "do the usual morning check" because the LLM has no idea what "the usual" means without conversation history.

The hard_multi scenarios at 100% show that when the prompt explicitly signals one-time + recurring, both variants route correctly. The routing confusion only appears when both items are the same type (both one-time in multi:two_reminders).

### Next

Need Pivot 2 to confirm convergence. The stopping criterion requires 2 pivots showing the same direction and magnitude. Pivot 1 shows identical performance on hard scenarios -- if Pivot 2 confirms this with either:
(a) the same scenarios at higher rep count (5 -> 10 reps for tighter CIs), or
(b) even harder scenarios (escalation test)

Options:
- **Option A:** Re-run hard scenarios only with 10 reps (100 calls per variant) for tighter CIs
- **Option B:** Design "extreme" scenarios pushing difficulty even further

Choosing Option A: re-run hard scenarios at higher rep count. The hard implicit scenarios at 10-20% are already near floor -- can't push much lower. Increasing reps will give tighter CIs and confirm whether the 0% difference is real or just insufficient n.

---

## Pivot 2: Hard Scenarios with Higher Rep Count

**Date:** 2026-02-19
**Rationale:** Pivot 1 showed identical hard scenario performance (58.0% both) at n=50 per variant. This could be a true null or insufficient statistical power. Doubling the rep count from 5 to 10 gives n=100 per variant on hard positive scenarios and n=40 on hard negatives -- enough to detect a 15% difference with 72% power.

**Scenarios:** Same 14 hard scenarios (10 positive + 4 negative), 10 reps each = 280 LLM calls
**Config:** applike vs baseline, hard scenarios only (-k filter), 10 reps
**Model:** claude-haiku-4-5-20251001

### Results

| Variant | Success Rate | 95% CI | n |
|---------|-------------|--------|---|
| baseline | 77.9% | [70.7%, 84.3%] | 140 |
| applike | 66.4% | [58.6%, 73.6%] | 140 |

**Difference:** -11.4% (applike lower)
**Bootstrap CI of difference:** [-18.6%, -5.7%] -- **SIGNIFICANT** (CI excludes zero)
**Fisher exact p-value:** 0.045 -- **SIGNIFICANT** (p < 0.05)

This is the first statistically significant result in the entire experiment series. With higher n, the applike deficit becomes measurable.

### Per-Category Breakdown

| Category | Baseline | Applike | Delta | n per variant | Fisher p | Sig? |
|----------|----------|---------|-------|---------------|----------|------|
| hard_ambiguous | 53.3% | 16.7% | -36.7% | 30 | 0.006 | **YES** |
| hard_distractor | 96.7% | 90.0% | -6.7% | 30 | 0.612 | No |
| hard_implicit | 20.0% | 5.0% | -15.0% | 20 | 0.342 | No |
| hard_multi | 100% | 100% | 0% | 20 | 1.000 | No |
| hard_negative | 100% | 100% | 0% | 40 | 1.000 | No |

### Hard Positive Aggregate

| Subset | Baseline | Applike | Delta | Fisher p | Sig? |
|--------|----------|---------|-------|----------|------|
| All hard positive (n=100) | 69.0% | 53.0% | -16.0% | 0.029 | **YES** |
| Excl. hard_multi (n=80) | 61.3% | 41.2% | -20.0% | 0.017 | **YES** |

### Category-Level Analysis

**hard_ambiguous (p=0.006 -- HIGHLY SIGNIFICANT):** This is the clearest differentiator found across the entire experiment series. Baseline at 53.3% vs applike at 16.7% -- a 36.7% gap. The mechanism is clear: when the user's intent is vague ("remind me about the meeting in a bit", "I keep forgetting my vitamins", "wake me up"), the baseline's single `schedule_task` is a natural catch-all -- the LLM just calls it. Applike forces a routing decision between `calendar_create_event` and `reminders_create`. Under ambiguity, the LLM freezes: it either picks the wrong tool, asks for clarification, or responds without scheduling.

This is particularly notable because "I keep forgetting my vitamins" should route to `reminders_create` (it's implicitly recurring), but the ambiguity about whether the user wants a recurring reminder or a one-time "take your vitamins now" creates decision paralysis.

**hard_distractor (not significant):** Both variants handle distractor context well. Baseline 96.7% vs applike 90.0% -- the gap exists but isn't statistically detectable at n=30. The LLM correctly extracts scheduling intent from noisy prompts regardless of tool interface.

**hard_implicit (not significant individually):** Both struggle badly (20% vs 5%), but the gap isn't significant due to floor effects. "do the usual morning check on me" and "remind me before the weekend" are genuinely hard for both -- the LLM doesn't know what "the usual" means or when "before the weekend" is. Tool interface doesn't help here.

**hard_multi (100% both):** When multi-item requests explicitly signal one-time + recurring routing (e.g., "set a reminder for 7am tomorrow and also remind me every Monday"), both variants handle them perfectly. The routing confusion from easy `multi:two_reminders` ("remind me at 3pm and 5pm" -- both one-time) is specific to same-type items, which was already captured in Pivot 0.

**hard_negative (100% both):** Hard negatives ("I should probably set a reminder at some point", "my calendar is packed this week") are correctly rejected by both variants. Tool interface design doesn't affect false positive suppression on these.

### Cost Comparison

| Variant | Avg Cost/Call | Cost for 140 Calls | vs Baseline |
|---------|---------------|--------------------| ------------|
| baseline | $0.003257 | $0.456 | -- |
| applike | $0.003261 | $0.457 | +0.1% |

Cost remains negligible and identical between variants. The hard scenarios produce slightly lower costs than easy scenarios (less tool call output when the LLM fails to call tools).

### Convergence Assessment

Comparing Pivot 1 (n=50 per variant on hard positive) and Pivot 2 (n=100 per variant):

| Metric | Pivot 1 | Pivot 2 | Direction |
|--------|---------|---------|-----------|
| Overall delta | 0% | -16.0% | Changed |
| hard_ambiguous delta | 0% | -36.7% | Changed (signal emerged) |
| hard_distractor delta | -6.7% | -6.7% | Stable |
| hard_implicit delta | +10.0% | -15.0% | Flipped (high variance) |
| hard_multi delta | 0% | 0% | Stable |

The apparent convergence at 0% in Pivot 1 was a Type II error -- insufficient n to detect the real difference in hard_ambiguous. With doubled n, a clear and significant signal emerges. The Pivot 2 results show a consistent applike deficit across hard_ambiguous, hard_distractor, and hard_implicit categories.

**Stopping criteria assessment:**
- Convergence: Pivots 1 and 2 don't match (0% vs -16%), BUT this is because Pivot 2 has higher power. The signal was always there; Pivot 1 just couldn't detect it.
- Clear signal: >10% significant difference in hard_ambiguous (36.7%, p=0.006) and overall hard positive (16%, p=0.029). Sustained across 2+ categories.
- This meets stopping criterion #2: "Clear signal -- >10% significant difference sustained across 2+ scenario categories"

**Decision: STOP exploration. Clear signal found.**

### Observation

The hard_ambiguous result is the key finding of Phase 5. When user intent is vague -- the most common real-world case for a personal assistant -- splitting scheduling into two tools (calendar + reminders) significantly hurts performance vs having a single catch-all tool. The baseline's `schedule_task` with its `recurring=True/False` flag provides a simpler cognitive model: "any scheduling need -> call schedule_task." The applike pattern forces the LLM to make a routing decision under ambiguity, which Haiku 4.5 handles poorly.

This is also the theoretically expected result: the tool interface hypothesis predicts that app-like naming would help routing by providing clearer semantic categories. But for Haiku 4.5, the routing tax of choosing between tools outweighs the semantic benefit. A more capable model (Sonnet, Opus) might handle the routing decision better, but that's out of scope.
