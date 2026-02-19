# ADR: Tool Interface Design for LLM Task Scheduling

**Status**: DECIDED -- Retain programmatic interface
**Date**: 2026-02-19
**Context**: Joi personal assistant agent, Claude Haiku 4.5 (claude-haiku-4-5-20251001)

---

## Problem Statement

The Joi agent exposes functionality to Claude through tool definitions -- function signatures with names, descriptions, and typed parameters. As the agent grows beyond its current 4-tool baseline (schedule_task, list_tasks, update_task, run_code) toward 15-20+ tools (media, home automation, file management), the question of how to design tool interfaces becomes architecturally significant. Interface patterns chosen now set precedent for every tool added later.

The core hypothesis comes from an "apps vs tools" framing: should LLM tool interfaces mirror human application paradigms (Calendar for one-time events, Reminders for recurring tasks) or remain as programmatic APIs (a single `schedule_task` with a `recurring` flag)? The intuition favoring app-like decomposition is that semantically distinct tools map to human mental models, potentially helping the LLM route requests more accurately.

This experiment tested that hypothesis in the task scheduling domain using Claude Haiku 4.5 -- the production model for Joi -- across 660 LLM calls over two phases, three exploration pivots, and 26 scenarios spanning easy to deliberately adversarial difficulty levels.

---

## Hypothesis

Decomposing `schedule_task` into semantically distinct tools (`calendar_create_event` for one-time events, `reminders_create` for recurring tasks) would improve routing accuracy by matching user mental models. The combined app-like variant also included parameter simplification (merging three timing parameters into a typed `when`) and description rewrites emphasizing purpose over mechanics.

To isolate causal factors, Phase 4 tested each design dimension independently:

- **Rename-only**: Change tool names without altering parameters or descriptions
- **Simplify-only**: Merge timing parameters into typed `when: int | str`
- **Description-A**: Purpose-focused description rewrite
- **Description-B**: Alternative description rewrite
- **App-like (combined)**: All changes simultaneously, plus tool decomposition (1 tool -> 2 tools)

---

## Methodology

### Eval Framework

The experiment used a custom eval framework built on pytest with YAML scenario definitions, typed dataclasses (`Scenario`, `ScenarioAssertion`), and a variant registry using decorator pattern. Each variant defines a tool set; scenarios define user messages and expected tool calls. Statistical analysis uses bootstrap BCa 95% confidence intervals (n_resamples=9999, seed=42) for reproducibility and Fisher exact tests for pairwise significance.

### Phase 4: Isolated Variable Experiments

- **Scope**: 5 variants (baseline + 4 isolated changes), 12 scenarios (7 positive + 5 negative), 5 repetitions each
- **Total**: 300 LLM calls, cost $1.07
- **Purpose**: Determine whether any single design dimension affects accuracy independently

### Phase 5: Full Comparison

- **Scope**: 2 variants (baseline vs app-like combined), up to 26 scenarios (17 positive + 9 negative), 5-10 repetitions
- **Total**: 660 LLM calls across 3 pivots, cost $2.25
- **Iterative design**: Easy scenarios first (ceiling calibration), then hard scenarios across 4 difficulty dimensions (ambiguous, multi-tool, distractor, implicit timing), then increased repetitions for statistical power
- **Stopping criteria**: Clear signal (>10% significant difference sustained across 2+ categories) or convergence (2 pivots showing same direction and magnitude)

### Difficulty Dimensions (Hard Scenarios)

| Dimension | Example | What It Tests |
|-----------|---------|---------------|
| hard_ambiguous | "remind me about the meeting in a bit" | Vague scheduling intent, unclear one-time vs recurring |
| hard_multi | "set a reminder for 7am and remind me every Monday" | Multi-tool routing with explicit type signals |
| hard_distractor | "What about the weather? Also remind me at 5pm to call the dentist" | Scheduling intent buried in noise |
| hard_implicit | "do the usual morning check on me" | Timing requires context the LLM doesn't have |

---

## Results

### Phase 4: Isolated Variables (300 LLM Calls)

| Variant | Success Rate | 95% CI | Delta vs Baseline | Significant? |
|---------|-------------|--------|-------------------|-------------|
| baseline | 95.0% | [86.7%, 98.3%] | -- | -- |
| rename | 91.7% | [81.7%, 96.7%] | -3.3% | No |
| simplify | 91.7% | [81.7%, 96.7%] | -3.3% | No |
| description_a | 95.0% | [86.7%, 98.3%] | 0.0% | No |
| description_b | 95.0% | [86.7%, 98.3%] | 0.0% | No |

No isolated variable produced a statistically significant change. Description rewrites had zero effect. Rename and simplify showed non-significant negative trends (-3.3% each, CIs including zero).

### Phase 5, Pivot 0: Easy Scenarios (120 LLM Calls)

| Variant | Success Rate | 95% CI | n |
|---------|-------------|--------|---|
| baseline | 98.3% | [91.7%, 100.0%] | 60 |
| applike | 93.3% | [84.0%, 98.3%] | 60 |

**Fisher p=0.364** -- not significant. Both variants perform near-identically at the 95%+ ceiling. The only weak signal: `multi:two_reminders` (baseline 80% vs applike 40%, n=5 per variant -- too small to conclude).

### Additive Null Model

Phase 4 isolated deltas: rename -3.3%, simplify -3.3%, description 0.0%. Predicted combined: 95.0% - 3.3% - 3.3% - 0.0% = 88.4%. Actual applike on easy scenarios: 93.3%. The app-like variant beats the additive prediction by +4.9 percentage points, suggesting mild positive synergy from the coherent "Calendar/Reminders" framing on easy tasks. However, this synergy disappears on hard scenarios.

### Phase 5, Pivot 2: Hard Scenarios with Adequate Power (280 LLM Calls)

Hard scenarios at 10 reps (n=100 per variant on hard positive):

| Variant | Success Rate | 95% CI | n |
|---------|-------------|--------|---|
| baseline | 77.9% | [70.7%, 84.3%] | 140 |
| applike | 66.4% | [58.6%, 73.6%] | 140 |

**Difference: -11.4%. Bootstrap CI: [-18.6%, -5.7%]. Fisher p=0.045 -- SIGNIFICANT.**

### Hard Scenario Breakdown (Pivot 2)

| Category | Baseline | Applike | Delta | n per variant | Fisher p | Significant? |
|----------|----------|---------|-------|---------------|----------|-------------|
| hard_ambiguous | 53.3% | 16.7% | -36.7% | 30 | 0.006 | **Yes** |
| hard_distractor | 96.7% | 90.0% | -6.7% | 30 | 0.612 | No |
| hard_implicit | 20.0% | 5.0% | -15.0% | 20 | 0.342 | No |
| hard_multi | 100% | 100% | 0% | 20 | 1.000 | No |
| hard_negative | 100% | 100% | 0% | 40 | 1.000 | No |

### Hard Positive Aggregate

| Subset | Baseline | Applike | Delta | Fisher p | Significant? |
|--------|----------|---------|-------|----------|-------------|
| All hard positive (n=100 each) | 69.0% | 53.0% | -16.0% | 0.029 | **Yes** |
| Excluding hard_multi (n=80 each) | 61.3% | 41.2% | -20.0% | 0.017 | **Yes** |

### Statistical Summary Across All Pivots

| Comparison | Scenario Set | Delta | 95% CI | Fisher p | Significant? |
|------------|-------------|-------|--------|----------|-------------|
| Pivot 0: applike vs baseline | Easy (n=60 each) | -5.0% | [-11.7%, 0.0%] | 0.364 | No |
| Pivot 1: applike vs baseline | All (n=130 each) | -3.8% | [-10.8%, 0.8%] | 0.526 | No |
| Pivot 1: hard only | Hard positive (n=50 each) | 0.0% | -- | 1.000 | No |
| Pivot 2: applike vs baseline | Hard (n=140 each) | -11.4% | [-18.6%, -5.7%] | 0.045 | **Yes** |
| Pivot 2: hard positive only | Hard positive (n=100 each) | -16.0% | -- | 0.029 | **Yes** |
| Pivot 2: hard_ambiguous | Ambiguous intent (n=30 each) | -36.7% | -- | 0.006 | **Yes** |

### Cost Comparison

| Pivot | Baseline Avg Cost/Call | Applike Avg Cost/Call | Difference |
|-------|----------------------|---------------------|-----------|
| 0 | $0.003676 | $0.003637 | -1.1% |
| 1 | $0.003463 | $0.003441 | -0.6% |
| 2 | $0.003257 | $0.003261 | +0.1% |

Cost is indistinguishable between variants. Total experiment cost across 660 LLM calls: $2.25.

---

## Decision

**REJECT** the app-like variant for task scheduling with Haiku 4.5. Retain `schedule_task` with `recurring` flag as the production interface.

The app-like variant introduces a measurable accuracy penalty on ambiguous scheduling requests (-36.7%, p=0.006) without providing any benefit on any other dimension. On easy scenarios both variants are equivalent; on hard scenarios the baseline significantly outperforms app-like. Cost is neutral. There is no compensating advantage to justify the accuracy trade-off.

**Scope of this decision**: This applies to Claude Haiku 4.5 on the task scheduling domain with the current tool count (4 tools). It is not a universal claim about tool interface design.

---

## Why It Didn't Work

Four root causes explain the null/negative result, each with supporting evidence from the experiment data.

### 1. Haiku 4.5 is near-optimal for structured tool use (~95% ceiling)

At a 95% baseline success rate on standard scenarios, there is no headroom for improvement. Any design change can only show noise or degradation. The Phase 4 isolated experiments confirmed this: all four individual changes (rename, simplify, description_a, description_b) produced CIs overlapping the baseline. The 5% failure rate in baseline is concentrated in inherently ambiguous scenarios (multi-tool routing, vague timing) that no tool naming change can address.

This is a ceiling effect, not a null result. The experiment didn't fail to find an effect -- it found that the baseline is already near-optimal for this model and domain.

### 2. Tool decomposition adds a routing failure mode

Splitting one tool into two forces the LLM to make a routing decision: is this request a calendar event or a reminder? When the user's intent is clear ("remind me every morning" -> `reminders_create`), routing works. When intent is ambiguous ("remind me about the meeting in a bit"), the LLM faces decision paralysis.

The evidence is direct: on `hard_ambiguous` scenarios, baseline achieved 53.3% while app-like achieved 16.7% -- a 36.7% gap (p=0.006). This is the largest and most significant effect found across all 660 LLM calls. The failure mode is specific: under ambiguity, Haiku 4.5 either picks the wrong tool, asks for clarification instead of scheduling, or responds without scheduling at all. The baseline's single `schedule_task` eliminates this routing decision entirely -- any scheduling need maps to one tool.

### 3. The hypothesis targeted the wrong layer

The experiment tested tool discovery and routing: can the LLM find and select the right tool? But the actual failure modes observed in hard scenarios are about intent inference (does the user want scheduling at all?) and parameter extraction (what does "in a bit" mean as a concrete time?).

Evidence: `hard_implicit` scenarios ("do the usual morning check on me", "remind me before the weekend") failed at 10-20% for both variants equally. The LLM doesn't know what "the usual" means or when "before the weekend" is -- this is a prompt interpretation challenge that no tool interface redesign can address. Similarly, `hard_distractor` scenarios (scheduling buried in conversational noise) showed near-identical performance (96.7% vs 90.0%, p=0.612). Tool naming doesn't help when the bottleneck is intent extraction from noisy input.

### 4. Model-specific ceiling

Haiku 4.5 is specifically optimized for tool use as part of Anthropic's model family. Its tool calling performance on well-structured APIs is already strong. A model with lower baseline tool accuracy (70-80%) would have more headroom for naming improvements to close. The experiment measures Haiku 4.5's specific behavior -- the routing tax observed under ambiguity may not apply to models that handle multi-tool disambiguation differently.

---

## What Would Need To Be True

Under what conditions would tool interface redesign (app-like decomposition) become beneficial?

### 1. More tools (20+)

With 3-4 scheduling tools in a 4-tool set, routing is trivial -- the LLM examines all tools on every call. At 20+ tools, discovery becomes a bottleneck. Semantic naming ("Calendar", "Reminders") could serve as category signals that help the LLM narrow its search space before examining individual tool signatures. The current experiment tested routing complexity at minimal tool count, where the routing cost outweighs any discovery benefit.

### 2. Weaker model

A model with a 70-80% baseline tool accuracy on well-formed requests would have 20-30 percentage points of headroom. In that regime, clearer semantic naming could meaningfully improve accuracy by providing stronger routing signals. Haiku 4.5's 95% baseline leaves only 5% headroom, making positive effects undetectable against noise.

### 3. Different task domain

Task scheduling maps to one semantic dimension: time. The one-time vs recurring split is the only natural decomposition, and it's a binary flag -- not enough semantic structure to justify separate tools. Domains with richer category structure (e.g., media: movies/shows/music/podcasts, or smart home: lights/climate/security/entertainment) might benefit from decomposition because the categories map to genuinely different parameter sets and behaviors, not just a flag difference.

### 4. Multi-turn with error recovery

This experiment used single-turn evaluation: one user message, one LLM response, pass/fail. Real conversations allow the LLM to self-correct after a wrong tool choice ("I scheduled that as a one-time event, did you want it recurring?"). App-like framing might help error recovery by making the tool categories more explicit in the conversation context. Single-turn eval cannot measure this potential benefit.

### 5. User-facing tool selection

If tools are exposed to end users (not just the LLM) -- for example, in a tool picker UI or a slash-command menu -- human-friendly naming has independent value regardless of LLM routing performance. "Calendar" and "Reminders" are immediately comprehensible to humans; `schedule_task(recurring=True)` is not. This experiment measured only LLM performance.

---

## Consequences

1. **Default to consolidated interfaces.** Future tool design for Joi should prefer fewer tools with flags (e.g., `manage_media(type=movie|show)`) over decomposed interfaces (e.g., separate `search_movies`, `search_shows`). This is a default, not a rule -- evaluate per domain.

2. **Model-specific, domain-specific finding.** This decision applies to Haiku 4.5 on task scheduling. Revisit when:
   - Switching to Sonnet or Opus as the primary model
   - Tool count exceeds 15
   - Adding a domain with rich category structure (media, smart home)

3. **Eval framework is reusable.** The YAML scenario definitions, bootstrap CI analysis, Fisher exact testing, and iterative exploration methodology (easy -> hard -> increase power) are directly applicable to future tool design experiments. The infrastructure investment pays forward.

4. **Total experiment cost: $2.25 across 660 LLM calls.** Rigorous empirical evaluation of tool design is cheap enough to be standard practice. Future tool additions should include a similar eval before committing to an interface pattern.

---

## Limitations

- **Single model.** Claude Haiku 4.5 only. Sonnet and Opus may handle routing decisions differently, potentially changing the cost-benefit calculus of tool decomposition.
- **Single domain.** Task scheduling with one semantic dimension (time). Domains with richer structure may behave differently.
- **Single-turn evaluation.** Real conversations are multi-turn with error recovery, clarification, and context accumulation. Single-turn eval captures first-attempt accuracy only.
- **Synthetic scenarios.** Hard scenarios were designed to stress-test specific difficulty dimensions. Real user behavior may cluster differently -- users may rarely produce `hard_ambiguous`-style requests, or may produce them more frequently than the scenario distribution suggests.
- **Sample sizes adequate for large effects.** The experiment can detect 15%+ differences with reasonable power. Subtle improvements (<5%) would require 500+ calls per condition to detect, and may not be practically meaningful.

---

## Open Questions

1. **Does the finding hold for Sonnet/Opus?** More capable models may handle the routing decision better, reducing the routing tax and potentially making decomposition net-positive.

2. **Would a hybrid approach perform differently?** App-like naming on a single tool (`calendar_schedule` instead of `schedule_task`, but keeping the `recurring` flag) provides semantic clarity without adding a routing decision.

3. **Does the routing tax scale linearly with tool count?** At 4 tools, adding 1 routing decision hurts. At 20 tools, the same routing decision might be negligible compared to the search space. There may be a crossover point.

4. **What is the crossover point where tool count makes decomposition beneficial?** The experiment tested at minimal tool count. The marginal cost of one routing decision may be fixed, while the marginal benefit of semantic categorization grows with tool count.

5. **How does multi-turn interaction change the picture?** If the LLM can self-correct tool choice errors in conversation, the routing tax of decomposition is reduced. App-like framing might even help by making the correction more natural ("I used Calendar but you might want Reminders for this").

---

## References

- Phase 4 results: `tests/eval/reports/phase4_summary.md` (300 LLM calls, 5 variants)
- Phase 5 exploration: `.planning/phases/05-full-comparison/EXPLORATION.md` (660 LLM calls, 3 pivots)
- Eval framework: `tests/eval/` (scenarios, variants, statistical analysis)
- Variant definitions: `tests/eval/variants/` (baseline, rename, simplify, description_a, description_b, applike)
