# Phase 10: Review and ADR - Research

**Researched:** 2026-02-20
**Domain:** Experiment data review, qualitative transcript analysis, ADR decision-making
**Confidence:** HIGH

## Summary

Phase 10 is an analysis phase, not an implementation phase. The inputs are 6 JSONL files (120 scenario results) from Phase 9, plus the existing v1.0 ADR (`docs/adr-tool-interface-experiment.md`) and the eval failure analysis (`docs/eval-failure-analysis.md`). The output is an updated ADR with a defensible ADOPT/REJECT/REVISIT decision grounded in clean data from v1.1.

The critical constraint is the **blind review protocol**: read transcripts before aggregate stats. This means the review must start with qualitative per-transcript assessment, recording observations without knowing pass rates. Only after qualitative review is complete should aggregate statistics be computed. The existing `tests/eval/stats.py` provides bootstrap CI and Fisher exact test utilities that can be reused for aggregate analysis.

Having read all 120 transcripts during this research, key observations are already forming: (1) both variants handle sanity, routing, and negative scenarios nearly identically, (2) the differentiating signal is in the ambiguous category where baseline tends to ask clarification while applike sometimes acts with assumed defaults, (3) the v1.1 data pattern is inverted from v1.0 for some ambiguous scenarios (applike now acts more decisively on some cases, baseline clarifies more), and (4) implicit scenarios produce near-identical clarification behavior from both variants.

**Primary recommendation:** Use Claude Code to perform a structured blind review directly from JSONL files, reading each transcript and recording per-scenario observations in a structured format. Then compute aggregate statistics using the existing `stats.py` utilities. Produce an ADR that updates or replaces the v1.0 ADR.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked. All decisions delegated to Claude's discretion.

### Claude's Discretion
**Review process:**
- How to structure the blind review (ordering, batching)
- Whether to review all 120 transcripts or use strategic sampling
- Tool choice: LangSmith traces, JSONL directly, Claude Code batch review, or combination
- How to record per-transcript observations

**Evaluation criteria:**
- Quality dimensions to assess (correctness, naturalness, ambiguity handling, tool selection)
- How to weight different quality dimensions
- What constitutes a "failure" vs "acceptable" vs "good" response

**ADR format and decision threshold:**
- Evidence threshold for ADOPT vs REJECT vs REVISIT
- ADR structure and level of detail
- How to present evidence (example transcripts, aggregate tables, both)

**Post-decision scope:**
- How to translate ADR conclusion into actionable next steps
- Whether to include migration plan in the ADR or defer to next milestone

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLS-02 | Results reviewed via LangSmith annotations + Claude Code JSONL analysis (blind review protocol) | JSONL files are self-contained with full transcript data (prompt + response_text + tool_calls). Claude Code can perform blind review directly from JSONL without LangSmith. LangSmith traces available as supplementary drill-down if needed. Blind protocol: review transcripts first, then compute stats. |
| ANLS-03 | ADR updated or replaced with conclusions from clean data | Existing v1.0 ADR at `docs/adr-tool-interface-experiment.md` provides the template and structure. v1.1 ADR should follow the same format but with clean data results. Key structural change: v1.1 uses zero-persona prompt (eliminating persona confound) and fixed timestamps (eliminating temporal confound). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.12 | JSONL parsing | Direct line-by-line reading, no dependencies needed |
| `tests/eval/stats.py` | (local) | Bootstrap CI, Fisher exact test, variant comparison | Already proven in v1.0 analysis. Provides `bootstrap_ci()`, `compare_variants()`, `fisher_exact_comparison()`. |
| scipy | (installed) | Statistical tests underlying stats.py | Already a project dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jq (CLI) | system | Quick JSONL querying from command line | Ad-hoc data exploration before structured analysis |
| loguru | (installed) | Logging analysis progress | Required by project standards |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct JSONL review | LangSmith UI | JSONL is fully self-contained, no external service needed. LangSmith adds drill-down but not needed for blind review. **Use JSONL.** |
| stats.py reuse | Pandas + manual stats | stats.py already implements exactly the right tests (BCa bootstrap, Fisher exact). **Reuse stats.py.** |
| Manual transcript reading | Automated LLM evaluation | Phase 10's whole point is human review — automated scoring was the v1.0 failure mode. **Read transcripts.** |

**Installation:**
No new dependencies needed.

## Architecture Patterns

### Recommended Output Structure
```
.planning/phases/10-review-and-adr/
    10-CONTEXT.md          # Already exists
    10-RESEARCH.md         # This file
    10-01-PLAN.md          # Blind review + aggregate analysis + ADR production
docs/
    adr-tool-interface-experiment.md  # Updated or replaced with v1.1 conclusions
```

### Pattern 1: Blind Review Protocol

**What:** A structured process for reviewing transcripts before seeing aggregate statistics, to prevent confirmation bias.

**Recommended approach:**

1. **Phase A — Qualitative transcript review (blind):**
   - Read all 120 transcripts from JSONL files
   - For each transcript, record: scenario_id, variant (baseline/applike), quality assessment, specific observations
   - Group by scenario (not by variant) — review all 3 runs of each scenario together to assess consistency
   - Use a rubric with dimensions: correctness, naturalness, appropriate ambiguity handling
   - Do NOT look at aggregate pass rates during this phase
   - Order: randomize or interleave variants to prevent systematic bias

2. **Phase B — Scoring and aggregation:**
   - Apply the rubric to produce per-transcript scores (good/acceptable/poor)
   - Compute aggregate statistics per variant, per category, overall
   - Use `stats.py` utilities for bootstrap CI and Fisher exact tests
   - Compare v1.1 results to v1.0 expectations

3. **Phase C — ADR synthesis:**
   - Combine qualitative observations with quantitative results
   - Draft decision: ADOPT/REJECT/REVISIT
   - Document evidence for and against each option
   - State the decision and its scope

**Why this order matters:** v1.0's biggest failure was evaluator bugs that encoded wrong assumptions about "correct" behavior. The blind protocol forces the reviewer to form opinions from actual transcripts before statistics can bias the interpretation. For example, v1.0 scored "asks for clarification" as failure — reading the actual transcripts makes it clear this is often the correct behavior.

### Pattern 2: Evaluation Rubric

**What:** A structured scoring system for individual transcripts. Recommended dimensions:

| Dimension | Good (3) | Acceptable (2) | Poor (1) |
|-----------|----------|-----------------|----------|
| **Tool selection** | Correct tool(s) for the intent, correct number of calls | Minor mismatch (e.g., one-time tool for recurring, but functionally works) | Wrong tool, missing tool call, or hallucinated tool |
| **Parameter quality** | Reasonable arguments that capture user intent | Mostly correct but with odd defaults (e.g., arbitrary 9am) | Wrong parameters, missing required info, contradicts user request |
| **Ambiguity handling** | Asks clarification when genuinely ambiguous, acts when clear | Either asks when it could have acted, or acts with reasonable defaults | Acts with bad defaults, or fails to recognize ambiguity |
| **Naturalness** | Response reads naturally, appropriate length | Slightly mechanical or verbose but functional | Robotic, excessively verbose, or confusing |

**Important nuance from eval-failure-analysis.md:** v1.0 treated "asks for clarification" as failure. v1.1 should treat clarification as a valid response when the prompt is genuinely ambiguous. The rubric above reflects this.

**Scoring system for statistics:**
- For aggregate comparison, reduce to binary: "good" or "acceptable" = pass (1.0), "poor" = fail (0.0)
- This feeds into the existing `stats.py` functions which expect `list[float]` of 0.0/1.0 scores

### Pattern 3: v1.1 vs v1.0 Comparison Framework

**What:** The v1.1 experiment differs from v1.0 in controlled ways. The ADR must document these differences and whether they change the conclusion.

| Dimension | v1.0 | v1.1 | Impact on Results |
|-----------|------|------|-------------------|
| System prompt | Full Joi persona (references tools by name) | Zero-persona (tool-agnostic) | Removes persona-tool confound. Baseline no longer advantaged by persona mentioning `schedule_task` |
| Timestamps | `datetime.now()` | Fixed `2026-02-15 10:00 UTC` (Saturday) | Reproducible temporal reasoning. "Before the weekend" now has known semantics. |
| Evaluators | Automated scoring with 5 known bugs | Human review (blind protocol) | No evaluator bugs possible. Clarification treated as valid response. |
| Scenarios | 26 from v1.0 (many with ceiling effects) | 20 new scenarios designed for differentiation | Better difficulty distribution targeting 40-70% band |
| Repetitions | 5-10 per scenario | 3 per scenario | Lower statistical power per scenario, but cleaner data |
| Tool sets | Persona included memory tools | Only scheduling tools | No `recall`/`remember` confound |

### Pattern 4: ADR Structure

**What:** The updated ADR should follow the same structure as the existing `docs/adr-tool-interface-experiment.md` but with v1.1 data.

**Recommended ADR sections:**
1. **Status** — DECIDED with decision
2. **Problem Statement** — Reuse from v1.0 ADR (same question)
3. **Hypothesis** — Same as v1.0
4. **Methodology** — Document v1.1 methodology and how it differs from v1.0
5. **Results** — v1.1 aggregate results with per-category breakdown, with v1.0 comparison
6. **Qualitative Findings** — Key transcript examples (the "why" behind the numbers)
7. **Decision** — ADOPT/REJECT/REVISIT with evidence
8. **Why (explanation)** — Root cause analysis of observed patterns
9. **Consequences** — What the decision means for future development
10. **Limitations** — What the experiment cannot conclude
11. **Comparison to v1.0** — Explicit section on what changed and why

### Anti-Patterns to Avoid

- **Stats-first review:** Computing aggregate pass rates before reading transcripts defeats the blind protocol. The whole point of Phase 10 is to avoid v1.0's mistake of trusting numbers generated by buggy evaluators.
- **Reusing v1.0 scoring criteria:** v1.0 penalized clarification questions and rewarded guessing. The new rubric must score clarification as valid for ambiguous scenarios.
- **Binary correctness only:** "Did the model call the right tool?" is too narrow. Quality dimensions include parameter quality, naturalness, and ambiguity handling.
- **Ignoring response stability:** With 3 runs per scenario, cross-run consistency matters. A variant that gives the same good answer 3/3 times is better than one that gives 2 great and 1 poor.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bootstrap CI computation | Custom bootstrap | `tests/eval/stats.py:bootstrap_ci()` | BCa method already implemented with seed=42, n_resamples=9999 |
| Fisher exact test | Custom significance test | `tests/eval/stats.py:fisher_exact_comparison()` | scipy-backed, handles 2x2 contingency tables |
| Variant comparison | Custom diff computation | `tests/eval/stats.py:compare_variants()` | Bootstrap CI on mean difference, significance detection |
| JSONL parsing | Custom parser | `json.loads()` per line | JSONL is newline-delimited JSON, stdlib handles it |
| ADR format | New template | Existing `docs/adr-tool-interface-experiment.md` | Same structure, updated content. Proven format. |

**Key insight:** Phase 10 produces analysis artifacts (observations, statistics, ADR), not code. The main "tool" is careful reading and structured thinking, not software engineering.

## Common Pitfalls

### Pitfall 1: Confirmation Bias from v1.0 Conclusions
**What goes wrong:** Reviewer enters Phase 10 expecting to confirm "REJECT applike" from v1.0, and unconsciously scores ambiguous cases to match that expectation.
**Why it happens:** v1.0 ADR exists and has a clear conclusion. Human tendency is to confirm prior beliefs.
**How to avoid:** The blind protocol is the primary defense. Additionally: read transcripts grouped by scenario (seeing both variants side by side), not grouped by variant. This makes it harder to form a narrative about one variant being "better."
**Warning signs:** Every ambiguous case scored the same way. No nuance in observations.

### Pitfall 2: Treating Clarification as Failure
**What goes wrong:** Scoring "asks for clarification" as poor/failure, as v1.0 evaluators did.
**Why it happens:** Binary "did it schedule?" mentality. v1.0 evaluators only checked for tool calls.
**How to avoid:** The rubric explicitly scores clarification as "good" when the prompt is genuinely ambiguous. Only score clarification as "poor" when the prompt has a clear, unambiguous scheduling request.
**Warning signs:** All "text-only" responses (no tool calls) scored as failures.

### Pitfall 3: Insufficient Attention to Ambiguous Category
**What goes wrong:** Spending equal time on all categories, including sanity (which will be trivially good for both) and negative (which will also be trivially good for both).
**Why it happens:** Methodical completeness feels virtuous. But sanity and negative scenarios exist to verify the floor/ceiling, not to provide signal.
**How to avoid:** Read all transcripts per the protocol, but allocate analytical attention proportional to where the signal is: ambiguous (6 scenarios, 36 results) and routing (4 scenarios, 24 results).
**Warning signs:** ADR has equal-length sections for sanity and ambiguous categories.

### Pitfall 4: Over-relying on n=3 Statistical Power
**What goes wrong:** Drawing firm conclusions from 3 repetitions of a single scenario.
**Why it happens:** Each scenario has only 3 runs per variant (vs v1.0's 5-10).
**How to avoid:** Use per-scenario runs for consistency assessment (do all 3 agree?), not for per-scenario significance testing. Statistical significance should come from category-level or overall aggregation (e.g., 18 observations for 6 ambiguous scenarios x 3 runs).
**Warning signs:** "Scenario X has 33% vs 67% pass rate" used as evidence (that's 1/3 vs 2/3 — meaningless with n=3).

### Pitfall 5: Scope Creep into Redesign
**What goes wrong:** The ADR starts proposing detailed tool redesigns or implementation plans instead of just making the decision.
**Why it happens:** Natural tendency to jump to solutions once the data is clear.
**How to avoid:** Keep the ADR focused on the decision and its immediate consequences. Detailed implementation plans belong in the next milestone.
**Warning signs:** ADR has sections like "Proposed New Tool Design" or "Migration Plan."

## Data Profile (from reading all 120 transcripts)

### Data Completeness
- 6 files x 21 lines (1 metadata + 20 scenario results) = 120 scenario results
- All 20 scenario IDs present in every file
- 0 truly empty responses (every result has either response_text or tool_calls or both)
- 35/120 results have empty response_text with non-empty tool_calls (tool-only responses — valid per Phase 9 decision)

### Response Pattern Overview (from full transcript read)

| Category | Scenarios | Results | Typical Pattern |
|----------|-----------|---------|----------------|
| sanity | 3 | 18 | Both variants: tool-only responses, correct tools, identical across runs |
| ambiguous | 6 | 36 | Mixed: some tool calls, some clarification questions. Variant differences visible here. |
| routing | 4 | 24 | Both variants: correct multi-tool calls, good parameter extraction |
| negative | 4 | 24 | Both variants: conversational responses, no tool calls. Correct behavior. |
| implicit | 3 | 18 | Both variants: mostly clarification questions, occasional action with defaults |

### Key Observations from Transcript Read

**Cross-run stability:** At temperature 0.2, most scenarios produce identical or near-identical responses across 3 runs. This is good for confidence (low variance) but limits per-scenario statistical analysis.

**Sanity category (18 results):** Both variants handle explicit scheduling perfectly. Baseline uses `schedule_task`, applike correctly routes to `calendar_create_event` (one-time) and `reminders_create` (recurring). Tool-only responses (no text) — efficient and correct.

**Ambiguous category (36 results) — primary signal area:**
- `vague_timing` ("in a bit"): Baseline asks clarification (3/3). Applike acts with default 15 min (3/3). **Inverted from v1.0** where baseline guessed and applike asked.
- `soon_laundry` ("soon"): Both ask clarification (3/3 each). No differentiation.
- `vitamins_habit` ("make sure I take my vitamins"): Baseline acts immediately with daily 9am recurring (3/3). Applike splits: run1 asks clarification, runs 2-3 act with daily 8am recurring. Cross-run inconsistency in applike.
- `wake_up` ("wake up on time tomorrow"): Baseline asks clarification (3/3). Applike acts with default 8am (3/3). Another inversion.
- `forgetting_plants` ("keep forgetting"): Both ask clarification (3/3). No differentiation.
- `later_reminder` ("later"): Both ask clarification (3/3). No differentiation.

**Routing category (24 results):** Both variants handle multi-item routing well. Applike correctly differentiates between `calendar_create_event` and `reminders_create`. This is the one area where tool decomposition shows a clear benefit — the separate tools make routing semantically explicit.

**Negative category (24 results):** Both variants correctly avoid scheduling tools. Conversational responses are natural and appropriate. No differentiation.

**Implicit category (18 results):**
- `before_weekend` (Saturday 10am fixed time): Both ask clarification. Correct — the weekend has already started.
- `usual_morning`: Both ask clarification. Correct — no context for "usual."
- `after_work`: Baseline asks clarification (3/3). Applike acts with default 5pm (2/3 runs), asks (1/3). Applike more decisive.

### Emerging Pattern: Decisiveness vs Clarification

The v1.1 data reveals a nuanced pattern not visible in v1.0:

- **Applike tends to act with assumed defaults** on ambiguous scenarios (vague_timing: 15 min, wake_up: 8am, after_work: 5pm)
- **Baseline tends to ask clarification** on ambiguous scenarios
- **This is the opposite of v1.0** where baseline guessed and applike asked

Likely explanation: The zero-persona prompt removes the bias. In v1.0, the Joi persona said "schedule_task()" which encouraged baseline to act. Without persona, the tool interface itself drives behavior. The `calendar_create_event` tool with its typed `when` parameter and concrete ISO datetime examples may signal to the model that it should provide a concrete time, encouraging action. The `schedule_task` tool with its more flexible `delay_seconds | when | recurring` interface may signal more uncertainty, encouraging clarification.

**This is a significant finding for the ADR:** The "routing tax" from v1.0 may be a persona artifact, not a genuine tool interface effect. The v1.1 zero-persona data tells a different story.

## Stats Reuse Strategy

The `tests/eval/stats.py` module provides exactly the right statistical tools. However, its `generate_report()` function expects a specific dict shape (`correct_tool_score`, `category`, `input_tokens`, `output_tokens`) that doesn't match the JSONL schema. Two options:

**Option A (recommended):** Write a small analysis script that:
1. Reads JSONL files
2. Applies the rubric scores from Phase A (qualitative review)
3. Transforms into the shape stats.py expects
4. Calls `bootstrap_ci()`, `compare_variants()`, `fisher_exact_comparison()`
5. Outputs aggregate tables for the ADR

**Option B:** Call `bootstrap_ci()` and `fisher_exact_comparison()` directly without using `generate_report()`. Simpler but produces less structured output.

Recommend Option A — it produces a reusable artifact and structured report.

## ADR Decision Framework

### Decision Criteria

| Decision | Condition |
|----------|-----------|
| **ADOPT** applike | Applike significantly better than baseline on key categories (ambiguous, routing), no significant degradation elsewhere |
| **REJECT** applike | Baseline significantly better OR no significant difference (default to simpler/existing) |
| **REVISIT** | Mixed signals (applike better on some categories, worse on others) OR insufficient data to decide |

### Evidence Requirements

For ADOPT: Clear positive signal in the category that matters most (ambiguous intent), supported by qualitative transcript evidence showing better responses. Statistical significance (Fisher p < 0.05) on at least one key category.

For REJECT: Either (a) clear negative signal in key categories, or (b) no meaningful difference — in which case the simpler option (baseline, which is already in production) wins by default. Occam's razor: don't add complexity without demonstrated benefit.

For REVISIT: Contradictory evidence across categories, or qualitative observations that challenge the quantitative scores, suggesting the rubric needs refinement or the experiment design missed important dimensions.

## Open Questions

1. **Should the ADR replace or amend the v1.0 ADR?**
   - What we know: The v1.0 ADR is at `docs/adr-tool-interface-experiment.md`. It documents a thorough experiment with known methodological issues.
   - What's unclear: Whether to update it in place (adding a v1.1 section) or create a new ADR that references v1.0.
   - Recommendation: **Replace in place.** The v1.0 ADR status was "DECIDED" based on data now known to be flawed. The v1.1 ADR supersedes it with clean data. Keep a "History" section acknowledging v1.0 findings.

2. **How to handle the "decisiveness vs clarification" nuance?**
   - What we know: Neither "acts with assumed defaults" nor "asks clarification" is objectively correct for ambiguous prompts. Both are valid strategies.
   - What's unclear: Which strategy the user (you) prefers for the production Joi agent.
   - Recommendation: Document both behaviors in the ADR. The decision should account for user preference, not just statistical comparison. If the user prefers a more proactive agent, applike's tendency to act may be a feature.

3. **Statistical power with n=3 runs?**
   - What we know: 3 runs per scenario at temperature 0.2 produces very low variance (most runs identical). Per-scenario Fisher tests are meaningless at n=3.
   - What's unclear: Whether category-level aggregation (n=18 for ambiguous, n=12 for routing) provides sufficient power.
   - Recommendation: Report per-category statistics but flag low power. Focus on qualitative evidence and consistency patterns rather than p-values for the decision.

## Sources

### Primary (HIGH confidence)
- `results/*.jsonl` (6 files) — Complete experiment data, all 120 transcripts read
- `docs/adr-tool-interface-experiment.md` — v1.0 ADR providing template and context
- `docs/eval-failure-analysis.md` — v1.0 post-mortem documenting 5 systemic bugs that v1.1 addresses
- `tests/eval/stats.py` — Statistical analysis utilities (bootstrap CI, Fisher exact, variant comparison)
- `tests/experiment/scenarios.py` — Scenario definitions with descriptions of what each tests
- `.planning/phases/09-run-experiments/09-01-SUMMARY.md` — Phase 9 execution summary confirming data completeness
- `.planning/phases/08-experiment-harness/08-RESEARCH.md` — Phase 8 research documenting experiment design rationale

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — ANLS-02, ANLS-03 requirement definitions
- `.planning/ROADMAP.md` — Phase 10 success criteria
- `tests/experiment/variants/baseline.py`, `applike.py` — Tool definitions showing exactly what each variant exposes

### Tertiary (LOW confidence)
- None. All findings are from direct codebase and data inspection.

## Metadata

**Confidence breakdown:**
- Data completeness: HIGH — all 120 transcripts read, data validated against Phase 9 summary
- Review methodology: HIGH — blind protocol is well-established in experimental review, adapted for this specific context
- Statistical approach: HIGH — reusing proven stats.py utilities, appropriate tests for binary outcomes
- ADR structure: HIGH — following established template from v1.0 ADR
- Qualitative findings: MEDIUM — preliminary observations from research-phase transcript reading. Full systematic review needed in Phase 10 execution.

**Research date:** 2026-02-20
**Valid until:** Indefinite (analysis methodology, not external dependency)
