# Differentiators Research: Beyond v1.1's Ceiling Effect

**Date**: 2026-02-20
**Context**: v1.1 experiment found 100% vs 100% pass rate (baseline vs applike), Fisher p=1.0. The binary pass/fail rubric on 20 scenarios with 4 tools is insufficient to discriminate. This document identifies 10 dimensions that could surface real differences, prioritized into a top-3 roadmap.

---

## Why v1.1 Hit a Ceiling

v1.1's null result has three root causes:
1. **Trivial tool count.** 3-4 tools means the LLM examines all tools on every call. No discovery/search problem.
2. **Binary rubric.** "Any poor = fail" collapses the quality gradient. Both variants achieve "acceptable" or better on everything.
3. **Single-turn isolation.** Each scenario is one prompt → one response. No compounding errors, no recovery paths.

The signal exists in the qualitative findings (decisiveness-vs-clarification pattern, cross-run stability divergence on `vitamins_habit`) but the measurement instrument can't capture it.

---

## Dimension 1: Scale Sensitivity (Tool Count)

**Hypothesis**: As tool count grows from 4 → 12 → 20+, app-like decomposition may help or hurt routing accuracy. At 4 tools, both interfaces are trivially discoverable. At 20 tools, semantic grouping (Calendar/Reminders) may reduce cognitive load for the LLM, or the extra tools may increase confusion.

**Measurement**: Pass rate and parameter quality across tool-count tiers: {4, 8, 12, 16, 20}. Add dummy tools from other domains (media, smart home, memory) to inflate the tool set without changing the scheduling interface.

**Experiment Sketch**:
- Keep the 20 v1.1 scenarios unchanged
- Create tool-count tiers by adding realistic dummy tools (e.g., `play_media`, `set_thermostat`, `search_contacts`)
- Run baseline vs applike at each tier, 3 reps, same zero-persona prompt
- Plot pass rate and rubric scores vs tool count

**Expected Signal**: Medium. Literature suggests tool routing degrades at 15+ tools. The question is whether decomposition helps or hurts at scale.

**Effort**: Medium (2-3 hours). Dummy tools are trivial to create. Infra reuse from v1.1.

---

## Dimension 2: Multi-Turn Error Recovery

**Hypothesis**: When the LLM makes a mistake (wrong tool, bad parameters), recovery behavior may differ between variants. App-like may recover faster because the error is scoped to a narrower tool, or slower because correcting requires re-routing between tools.

**Measurement**: Inject deliberate error signals (e.g., tool returns "Error: invalid cron expression") and measure: (a) does the LLM retry correctly, (b) how many turns to recover, (c) does it switch tools or fix parameters.

**Experiment Sketch**:
- Extend experiment harness to support multi-turn: prompt → tool call → error response → retry
- 5-8 error scenarios: invalid cron, past datetime, missing required field, ambiguous tool match
- Measure recovery rate, turns-to-recovery, tool-switching frequency
- Compare baseline (single tool to fix) vs applike (may need to switch calendar↔reminders)

**Expected Signal**: High. This is where interface complexity should show real differences. v1.1 was single-turn so this dimension was completely untested.

**Effort**: High (4-6 hours). Requires multi-turn harness extension, new scenarios, new rubric dimensions.

---

## Dimension 3: Parameter Quality Gradient

**Hypothesis**: v1.1's binary rubric (pass/fail) masks quality differences in parameter values. E.g., for "remind me to grab the package in a bit," both variants pass, but one might produce `delay_seconds=900` (reasonable) vs `when="15 minutes"` (also reasonable but less precise). A continuous quality score would surface these differences.

**Measurement**: Replace binary pass/fail with a continuous rubric (0-10) across dimensions:
- Temporal precision (how specific is the time?)
- Parameter completeness (all relevant fields populated?)
- Semantic appropriateness (recurring vs one-time choice quality)
- Cron expression quality (for recurring: correct syntax, appropriate granularity)

**Experiment Sketch**:
- Re-score the existing 120 v1.1 transcripts on the continuous rubric (no new LLM calls needed)
- Compute mean quality scores per variant per category
- Use Wilcoxon signed-rank test instead of Fisher exact (handles continuous data)

**Expected Signal**: Medium-High. The qualitative findings already show behavioral differences (decisiveness vs clarification). A continuous rubric should quantify what the binary one misses.

**Effort**: Low (1-2 hours). No new experiment runs — just re-scoring existing transcripts.

---

## Dimension 4: Compositional Complexity

**Hypothesis**: When tasks require composing multiple tool calls (e.g., "set up my morning routine: wake up at 7, exercise at 7:30, breakfast at 8"), decomposed tools may produce better or worse results because each sub-task must be routed independently.

**Measurement**: Introduce compositional scenarios requiring 3-5 tool calls with dependencies. Score: correct tool count, parameter consistency across calls (e.g., times don't overlap), logical ordering.

**Experiment Sketch**:
- 6-8 compositional scenarios of increasing complexity (2-call, 3-call, 5-call)
- Include dependency constraints ("exercise AFTER wake-up", "review BEFORE bed")
- Measure: correct call count, inter-call consistency, temporal ordering correctness
- Compare baseline (all calls to schedule_task with varying params) vs applike (must route each to correct tool)

**Expected Signal**: Medium. Routing pressure increases linearly with call count, and applike adds a routing decision per call.

**Effort**: Medium (2-3 hours). New scenarios needed, existing harness works if single-turn is sufficient.

---

## Dimension 5: Cross-Model Generalization

**Hypothesis**: v1.1 tested only Claude Haiku 4.5. Different models may handle tool interfaces differently. A smaller model (e.g., Haiku 3.5) may struggle more with applike's routing, while a larger model (e.g., Sonnet 4.6) may handle both trivially.

**Measurement**: Run the same 20 scenarios on 2-3 additional models. Compare delta-between-variants across models.

**Experiment Sketch**:
- Models: Claude Haiku 3.5 (weaker), Claude Sonnet 4.6 (stronger), optionally GPT-4o-mini (cross-family)
- Same 20 scenarios, 3 reps, same rubric
- Plot variant-delta vs model capability
- Hypothesis: delta increases as model capability decreases

**Expected Signal**: Medium-High. If Haiku 3.5 shows a real gap, it validates the interface design matters — just not at Haiku 4.5's capability level.

**Effort**: Medium (2-3 hours). Mostly infra work to swap model. Cost varies by model.

---

## Dimension 6: Latency and Streaming Behavior

**Hypothesis**: App-like decomposition may affect time-to-first-token (TTFT) and total latency because the model must evaluate more tool definitions. The 9% token overhead in v1.1 may translate to measurable latency differences.

**Measurement**: Wall-clock TTFT and total response time per scenario. Token-level streaming analysis if available.

**Experiment Sketch**:
- Add timing instrumentation to experiment harness (start_time, first_token_time, end_time)
- Run 20 scenarios × 3 reps × 2 variants with timing
- Compare mean TTFT and total latency
- Correlate with tool definition size (tokens in system prompt)

**Expected Signal**: Low-Medium. The 9% token difference is small. Latency differences may be noise-level at current API speeds.

**Effort**: Low (1 hour). Just add timing to existing harness.

---

## Dimension 7: Persona Interaction Effects

**Hypothesis**: v1.1 used zero-persona to eliminate confounds, but production uses a full Joi persona. The interaction between persona and tool interface may produce different results than either alone. v1.0 showed persona inverted the behavioral pattern — this deserves systematic study.

**Measurement**: 2×2 factorial design: {baseline, applike} × {zero-persona, full-persona}. Measure pass rate and decisiveness-vs-clarification pattern across all four conditions.

**Experiment Sketch**:
- 4 conditions: baseline+zero, baseline+persona, applike+zero, applike+persona
- Same 20 scenarios, 3 reps
- 240 total LLM calls (2× v1.1 cost)
- Analyze interaction effect: does persona flip the behavioral pattern (as v1.0 suggested)?

**Expected Signal**: High. v1.0→v1.1 pattern inversion is the strongest evidence that persona interacts with tool interface. A 2×2 design isolates this cleanly.

**Effort**: Medium (2-3 hours). Requires the full Joi persona prompt. Existing infra handles the rest.

---

## Dimension 8: User Satisfaction Proxy

**Hypothesis**: Even when both variants are "correct," users may prefer one style over another. The decisiveness-vs-clarification split is a UX preference, not a correctness issue. A preference-based evaluation may discriminate where correctness doesn't.

**Measurement**: LLM-as-judge pairwise comparison. Present both variant responses side-by-side to a judge model, ask "which response would a user prefer?" with explanation.

**Experiment Sketch**:
- Take the 120 v1.1 transcripts, pair baseline vs applike for each scenario × run
- Use a strong judge model (Claude Sonnet 4.6) for pairwise preference
- Compute win rate per variant overall and per category
- Validate with 2-3 human judges on a subset

**Expected Signal**: Medium. Preference is subjective but may reveal consistent patterns. The decisiveness-vs-clarification split should produce a clear preference signal on ambiguous scenarios.

**Effort**: Low-Medium (1-2 hours). No new experiment runs. Judge prompt design is the main work.

---

## Dimension 9: Prompt Perturbation Robustness

**Hypothesis**: Both variants achieve 100% on the exact v1.1 prompts, but may differ in robustness to prompt variations. Typos, rephrasing, multilingual input, or adversarial phrasing may break one variant more than another.

**Measurement**: Generate 3-5 perturbations of each scenario prompt (synonym substitution, typo injection, informal register, partial translation). Measure pass rate on perturbed prompts.

**Experiment Sketch**:
- Perturbation types: synonym ("remind" → "alert"), typo ("reming me"), informal ("yo set a thing for 3"), partial non-English ("rappelle-moi at 3pm")
- 20 scenarios × 4 perturbations = 80 perturbed prompts
- Run each × 2 variants × 3 reps = 480 calls
- Compare robustness (pass rate on perturbed vs original)

**Expected Signal**: Medium. Consolidated tools with flexible parameters may be more robust to input variation because there's only one tool to match. But applike's semantic naming may help with synonym-type perturbations.

**Effort**: High (4-6 hours). Many new prompts to create and validate. High call count.

---

## Dimension 10: Tool Description Sensitivity

**Hypothesis**: The decisiveness-vs-clarification pattern in v1.1 was driven by tool parameter design, not tool naming. If we modify tool descriptions (e.g., add "ask for clarification when timing is ambiguous" to applike, or "use reasonable defaults when timing is vague" to baseline), the behavioral pattern should invert.

**Measurement**: Create description variants that explicitly encourage or discourage clarification-seeking. Measure behavioral flip rate.

**Experiment Sketch**:
- 4 conditions: {baseline, applike} × {clarification-encouraging, action-encouraging} descriptions
- Focus on the 6 ambiguous + 3 implicit scenarios (9 scenarios where the pattern manifests)
- 9 scenarios × 4 conditions × 3 reps = 108 calls
- Measure: does description override the default behavioral tendency?

**Expected Signal**: High. v1.1 ADR already identified tool parameter design as the causal mechanism. This dimension tests that hypothesis directly.

**Effort**: Low-Medium (1-2 hours). Small scenario set, minimal new infra.

---

## Summary Table

| # | Dimension | Signal | Effort | New Calls | Key Insight |
|---|-----------|--------|--------|-----------|-------------|
| 1 | Scale sensitivity | Medium | Medium | ~600 | Does tool count break the ceiling? |
| 2 | Multi-turn error recovery | High | High | ~100 | Recovery paths differ by interface |
| 3 | Parameter quality gradient | Medium-High | Low | 0 | Re-score existing data continuously |
| 4 | Compositional complexity | Medium | Medium | ~100 | Multi-call routing pressure |
| 5 | Cross-model generalization | Medium-High | Medium | ~360 | Capability-dependent effects |
| 6 | Latency/streaming | Low-Medium | Low | ~120 | Token overhead → latency? |
| 7 | Persona interaction | High | Medium | ~240 | 2×2 factorial: persona × interface |
| 8 | User satisfaction proxy | Medium | Low-Medium | 0 | Preference-based discrimination |
| 9 | Prompt perturbation robustness | Medium | High | ~480 | Input variation resilience |
| 10 | Tool description sensitivity | High | Low-Medium | ~108 | Causal test of v1.1's mechanism |

---

## Prioritized Top-3 Roadmap for Next Milestone

### Priority 1: Parameter Quality Gradient (Dimension 3)

**Why first**: Zero marginal cost — re-scores existing 120 transcripts. Validates whether the continuous rubric can discriminate before investing in new experiments. If it can't, the other dimensions need a different measurement approach too.

**Deliverable**: Continuous quality scores for all 120 transcripts. Statistical test (Wilcoxon) for variant differences. Go/no-go for continuous rubric in future experiments.

**Time estimate**: 1-2 hours.

### Priority 2: Tool Description Sensitivity (Dimension 10)

**Why second**: Directly tests v1.1's causal hypothesis (parameter design drives behavior) with minimal cost (~108 calls). If confirmed, it reframes all future tool design as "description engineering" rather than "interface architecture." This has immediate product implications for how we write tool definitions.

**Deliverable**: Evidence for/against description-driven behavioral control. If confirmed: design guidelines for tool descriptions that control LLM response style.

**Time estimate**: 1-2 hours.

### Priority 3: Persona Interaction Effects (Dimension 7)

**Why third**: The v1.0→v1.1 pattern inversion is the most surprising finding. A 2×2 factorial cleanly isolates persona as a variable. This matters for production because Joi runs with a full persona — the zero-persona result may not generalize.

**Deliverable**: 2×2 interaction analysis. Clear answer to "does the v1.1 REJECT hold under persona?" If not, the decision needs revisiting.

**Time estimate**: 2-3 hours.

### Total roadmap: ~5-7 hours, ~350 LLM calls, ~$1.50 estimated cost

---

## Deferred Dimensions

- **Scale sensitivity** (D1): Valuable but requires dummy tool creation infrastructure. Do after P1-P3 validate the measurement approach.
- **Multi-turn error recovery** (D2): Highest signal but highest effort. Requires multi-turn harness. Save for a dedicated milestone.
- **Cross-model generalization** (D5): Important for generalizability claims but expensive. Run after the measurement approach is proven.
- **Prompt perturbation** (D9): Highest call count. Run only if earlier dimensions show the measurement approach works.
- **Compositional complexity** (D4), **Latency** (D6), **User satisfaction** (D8): Lower priority, run opportunistically.
