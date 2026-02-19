# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Validated architectural decisions backed by evidence, not gut feel
**Current focus:** Phase 4 — Isolated Variable Experiments

## Current Position

Phase: 4 of 6 (Isolated Variable Experiments) COMPLETE
Plan: 2 of 2 in current phase (04-02 COMPLETE)
Status: Phase 4 complete — all isolated experiments run, no significant differences found
Last activity: 2026-02-19 — Run 5-variant experiment (300 LLM calls), generate summary report

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 5.5min
- Total execution time: 44min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Codebase Alignment Audit | 1 | 5min | 5min |
| 2. Eval Framework | 3 | 10min | 3.3min |
| 3. App-Like Variant Design | 2 | 5min | 2.5min |
| 4. Isolated Variable Experiments | 2 | 24min | 12min |

**Recent Trend:**
- Last 5 plans: 02-03 (3min), 03-01 (2min), 03-02 (3min), 04-01 (4min), 04-02 (20min)
- Trend: 04-02 longer due to 300 real LLM calls (~16min test runtime)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 6 phases derived from 12 requirements. Audit first, then eval infra, then experiment, then ADR.
- Roadmap: Each phase has an approval gate — no automatic progression.
- Audit: Memory (Mem0) is highest-impact misalignment (score 8/10) -- needs architectural replacement in future milestone.
- Audit: Tasks subsystem confirmed as correct first experiment target for apps-vs-tools hypothesis.
- Audit: 3 subsystems (Graph Core, Context Management, Sandbox) have zero misalignments -- no action needed.
- Eval: YAML scenarios use typed dataclasses (Scenario, ScenarioAssertion) not raw dicts
- Eval: Variant registry uses decorator pattern -- new variant = decorate a function in a new file
- Eval: Baseline variant includes 4 tools (schedule_task, list_tasks, update_task, run_code) matching production
- Eval: Eval model hardcoded to claude-haiku-4-5-20251001 for cost-effective consistency
- Eval: Dual-mode cache (LANGSMITH_TEST_CACHE env var) for real vs cached LLM responses
- Eval: LangSmith feedback logged per test: correct_tool, correct_count, token metrics
- Eval: Bootstrap BCa CIs with fixed seed (rng=42) for reproducible statistical analysis
- Eval: record_eval_result uses keyword-only args for decoupling from EvalResult dataclass
- Eval: Autouse session fixture generates JSON report after all eval tests complete
- Variants: Single-dimension isolation -- each variant changes exactly ONE variable from baseline
- Variants: Simplify uses typed when: int | str merging 3 timing params (validated pattern from old eval)
- Variants: All isolated variants share baseline system prompt (only full app-like changes it)
- Variants: All experimental variants exclude run_code (orthogonal noise reduction)
- Variants: App-like splits schedule_task into calendar_create_event (one-shot) and reminders_create (recurring)
- Variants: App-like absorbs retry_in/question/message into single detail param
- Variants: App-like persona patching via regex replacement of Background Tasks section
- Variants: Token budget confirmed -- applike at +3.3% vs baseline (well within 10%)
- Variants: Parity matrix covers 9 capabilities x 6 variants with absorption notes
- Eval: schedule_tool_names fallback pattern (plural or [singular]) for multi-tool variant filtering
- Eval: Three-tier staggered timing: delay_seconds -> int when -> distinct string when (no tool-name gating)
- Experiment: No isolated variable produces statistically significant improvement over baseline (n=60 per variant)
- Experiment: Baseline already strong at 95% success rate -- ceiling effect limits differentiability
- Experiment: Rename and simplify show non-significant negative trend (-3.3% each)
- Experiment: Description rewrites (A and B) indistinguishable from baseline and each other (all 95%)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 04-02-PLAN.md — Phase 4 complete, ready for Phase 5 (combined comparison)
Resume file: .planning/phases/04-isolated-variable-experiments/04-02-SUMMARY.md
