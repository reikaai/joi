# Feature Landscape

**Domain:** Agent eval pipeline for tool interface experiments
**Researched:** 2026-02-20
**Mode:** Subsequent milestone -- rebuilding on existing v1.0 eval infrastructure

## Table Stakes

Features the eval pipeline must have for trustworthy experiment results. Missing = experiment data is unreliable.

### Response Capture

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Full content serialization (text + tool calls) | v1.0 bug: `response.content` as list was discarded to `""`. Cannot diagnose failures without re-running. Anthropic says "capture the full messages array." | Low | Fix `_serialize_response` to handle list content. When tool calls present, `content` is `[{"type": "text", "text": "..."}, {"type": "tool_use", ...}]`. Serialize all text blocks. |
| Tool call args + IDs captured | Already partially done (`name`, `args`, `id`). Need to verify completeness. | Low | Already in `_serialize_response`. Verify `id` is always present. |
| Token usage metadata captured | Already done via `usage_metadata`. | Done | Working in v1.0 -- `input_tokens`, `output_tokens`, `total_tokens`. |
| Response timestamp | Needed for batch review ordering and staleness detection of cached results. | Low | Add `datetime.now(UTC).isoformat()` to serialized response. |
| Scenario-level JSONL log | Each eval run should append a structured record to a JSONL file: scenario_id, variant, prompt, full response, eval result, timestamp. This is the batch review data source. | Med | New. Write one JSONL per experiment run. This replaces LangSmith as the primary review artifact (free tier limitations, offline review need). |

### Evaluator Fixes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fix `_check_has_timing` for `schedule` param | v1.0 bug: `has_timing` checks `delay_seconds` and `when` but not `schedule`. Causes false failures on all applike cron-based responses. 10/10 false FAILs on `hard_multi:onetime_plus_recurring`. | Low | Add `or _looks_like_cron(args.get("schedule", ""))` to `_check_has_timing`. |
| Fix persona-tool mismatch in eval | v1.0 bug: persona says "call recall() first" but eval strips `recall` tool. Haiku obeys persona, generates invalid tool call, inflates failure counts. | Med | Two options: (a) include mock recall/remember tools in eval, or (b) strip memory instructions from eval persona. Option (b) is better -- it isolates what we are testing. |
| Clarification scored as valid outcome | v1.0 systemic flaw: single-turn eval marks clarification as failure. But "before the weekend, remind me" genuinely needs clarification. Anthropic: "read transcripts carefully to verify failures are fair." | Med | New assertion type: `allows_clarification`. When present, scenario passes if agent either (a) calls expected tool OR (b) produces text containing a question. Details in Evaluator Patterns section below. |
| Partial credit scoring | Binary pass/fail hides nuance. An agent that calls the right tool with wrong timing is closer to correct than one that calls no tool at all. | Med | Replace binary `passed` with multi-dimensional scores: `tool_selection` (0/1), `parameter_quality` (0-1), `behavioral_appropriateness` (0-1). Aggregate as weighted composite. |

### Experiment Isolation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Zero-persona eval mode | v1.0 persona leaks confound results: persona says "call recall()" but tool set lacks `recall`. Need to strip persona to isolate tool interface effects from personality effects. | Med | Create a minimal eval persona: "You are a task management assistant. Use the provided tools to help users. Current time: {timestamp}." No personality, no memory instructions, no references to unavailable tools. |
| Tool parity enforcement | v1.0 had tool capability gaps between variants (applike lacks `run_code`, baseline lacks calendar tools). Need to verify equivalent capabilities across variants for fair comparison. | Low | Automated check: for each variant, list available tool names and parameter schemas. Flag any variant that cannot express a scenario's expected behavior. Already partially documented in `parity_matrix.md`. |
| Fixed timestamp injection | Eval runs at different times of day get different results ("remind me at 5pm" behaves differently at 4pm vs 6pm). Anthropic: "stable environment, each trial isolated." | Low | Hardcode eval timestamp in system message: `[2026-02-20 10:00 UTC]`. Already partially done but using `datetime.now()`. |

### Run Metadata

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Experiment metadata in output | Record model, git commit, timestamp, variant definitions alongside results. Required for reproducibility. | Low | Add metadata dict to report JSON. |
| Cache invalidation strategy | Old cache has broken serialization from v1.0 bug. Must flag or re-record. | Low | Delete cache dir or add schema version marker. |

## Differentiators

Features that make the eval meaningfully better than baseline v1.0. Not expected in a minimal eval, but address the 5 systemic bugs found.

### Batch Review Workflow

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| JSONL capture with full context | Capture everything needed for post-hoc review: prompt, full response (text + tools), eval scores, variant, scenario metadata. Review with Claude Code instead of LangSmith UI. | Med | Core data format. One JSONL file per experiment run, each line is one scenario execution. Claude Code can read and analyze. |
| Review script for Claude Code | Script that reads JSONL, formats scenario results as readable markdown table, highlights failures with full response text. Run as `uv run python scripts/eval_review.py data/experiment_20260220.jsonl`. | Med | Simple Python script. Formats output for terminal or pipes to markdown. Key value: human reads the actual agent response, not just pass/fail. |
| Diff mode between experiment runs | Compare two JSONL files side-by-side: which scenarios flipped pass/fail, which response text changed. Essential for "did the fix actually help?" | Med | `eval_review.py diff run_a.jsonl run_b.jsonl`. Show changed outcomes only. |
| Failure transcript viewer | For each failing scenario, show: prompt, expected behavior, actual response text, actual tool calls, which assertion failed. Anthropic: "you won't know if your graders are working unless you read transcripts." | Low | Part of the review script. Filter to failures only, print full context. This is what v1.0 couldn't do because response text was discarded. |

### Advanced Evaluator Patterns

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Behavioral classification evaluator | Instead of just pass/fail, classify agent behavior: `tool_called_correctly`, `clarification_asked`, `wrong_tool`, `hallucinated_tool`, `no_action`, `info_gathering`. Each classification maps to a score for the scenario. | Med | New evaluator function. Returns behavior enum + score. Replaces binary assertions with richer signal. Key for ambiguous scenarios. |
| Info-gathering scored as partial success | Agent calls `calendar_list_events` before scheduling = gathering context. This is smart behavior, not failure. Score: 0.5 for info-gathering without action, 1.0 for info-gathering + correct action. | Low | Extend `evaluate_tool_calls` to recognize info-gathering tools (list_tasks, calendar_list_events, recall) as valid intermediate steps. |
| Scenario difficulty calibration | Tag scenarios with expected pass rate ranges based on human judgment. Flag evaluator if observed rate diverges wildly (e.g., "easy" scenario with <50% pass rate suggests evaluator bug, not model bug). | Low | Add `expected_pass_rate: [0.8, 1.0]` to YAML. Assert in report generation. Early warning for evaluator regressions. |

### Scenario Design Improvements

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Ambiguity-aware scenario tagging | Tag scenarios as `unambiguous` (single correct answer), `ambiguous_timing` (when is unclear), `ambiguous_intent` (what is unclear), `ambiguous_routing` (which tool unclear). Different scoring rules per tag. | Low | YAML field `ambiguity: unambiguous|timing|intent|routing`. Evaluator adjusts scoring: unambiguous = strict, ambiguous = allows clarification. |
| Multiple valid outcomes per scenario | Some scenarios have 2+ correct behaviors. "I keep forgetting vitamins" could be: (a) schedule recurring reminder, (b) ask about preferred time, (c) store memory note + ask about scheduling. All are valid. | Med | YAML field `valid_outcomes` listing acceptable behavior patterns. Evaluator checks if actual behavior matches ANY valid outcome. |
| Ground truth response examples | For each scenario, include 1-2 example "good" responses (text + tool calls) from manual testing. Used for batch review comparison, not for automated scoring. | Low | YAML field `examples` with human-written ideal responses. Displayed in review script alongside actual response. Helps reviewer calibrate expectations. |

## Anti-Features

Features to explicitly NOT build for v1.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| LLM-as-judge per scenario | Expensive ($0.01-0.05 per judgment with Opus), non-deterministic, hard to debug why a judgment was given. The whole point is batch review with human (Claude Code) post-hoc. We have ~25 scenarios, not 2500. | Deterministic evaluators for automated scores. JSONL capture for human/Claude review. |
| Multi-turn eval sequences | Adds massive complexity (conversation state management, turn routing, response simulation). v1.0's single-turn limitation is real but the fix is better single-turn design, not multi-turn. | Design single-turn scenarios that have clear correct answers. For ambiguous scenarios, score clarification as success. Multi-turn can be a v1.2 feature. |
| Custom web UI for review | Solo developer, local-only setup. Building a web app for reviewing 25 scenarios is massive over-engineering. | CLI scripts + JSONL files + Claude Code review. Terminal is the UI. |
| Automated regression detection | Building CI that detects eval regressions between commits. Premature -- eval is still being designed, baselines are unreliable. | Manual comparison via diff script. Automated regression makes sense after v1.1 proves the eval is trustworthy. |
| Real-time eval dashboard | Streaming results to a dashboard during eval runs. | Terminal output from pytest + post-hoc JSONL review. |
| Prompt optimization loops | Automatically tweaking system prompts to maximize eval scores. | The experiment tests tool interfaces, not prompt quality. Prompt optimization is a different concern. |
| Full-agent E2E eval mode | 10-100x more expensive, much flakier, not needed for tool interface comparison. | Keep single-call eval; E2E is a separate concern. |
| New eval dependencies (DeepEval, Promptfoo, etc.) | Already have a working framework; adding tools adds complexity. | Fix what exists; it already does 90% of what's needed. |
| Database storage (SQLite/Postgres) | Unnecessary complexity for eval data that fits in flat files. | JSONL for review, JSON for reports, git for versioning. |
| Automatic scenario generation via LLM | Circular reasoning risk; LLM generates what it finds easy to solve. | Hand-craft scenarios based on observed failure modes. |

## Feature Dependencies

```
Serialization Fix ──> JSONL Capture Log ──> Review Script ──> Diff Mode
                  └──> Cache Invalidation
                                        └──> Failure Transcript Viewer

has_timing Bug Fix ──────> Re-run Experiments

Persona-Tool Fix ──> Zero-Persona Mode ──> Fair Variant Comparison
                                       └──> Tool Parity Enforcement

Clarification Scoring ──> Ambiguity Tags ──> Multiple Valid Outcomes
                     └──> Behavioral Classification Evaluator

Fixed Timestamp ──> Reproducible Results ──> Cached Baseline Validity

Run Metadata (independent) ──> Run Archival
```

## Evaluator Pattern Details

### Current State (v1.0)

The existing evaluators are pure deterministic checks:
- `_check_has_timing`: Does the tool call have a timing parameter?
- `_check_staggered_timing`: Are delays strictly increasing?
- `_check_is_recurring`: Does the call indicate recurring?
- `_check_no_run_code`: Did the agent avoid run_code fallback?

These work for unambiguous scenarios ("remind me in 5 min") but fail for ambiguous ones ("remind me before the weekend").

### Recommended Evaluator Architecture (v1.1)

**Layer 1: Behavioral Classifier (deterministic, always runs)**

Classify the agent's response into one of:
- `TOOL_CALLED` -- called expected tool with parameters
- `CLARIFICATION_ASKED` -- responded with a question (detected via `?` in response text + no tool calls, or tool call + question text)
- `INFO_GATHERED` -- called an info-gathering tool (list, recall, calendar_list) without scheduling
- `WRONG_TOOL` -- called a tool not in expected set
- `HALLUCINATED_TOOL` -- called a tool not in bound schema
- `NO_ACTION` -- no tool calls, no question (just text response)

**Layer 2: Scenario-Specific Scoring (deterministic, per-scenario rules)**

Each scenario defines which behaviors score how:

```yaml
# Unambiguous scenario
- id: single:reminder
  prompt: "remind me to call mom in 5 min"
  scoring:
    TOOL_CALLED: 1.0          # correct
    CLARIFICATION_ASKED: 0.3  # unnecessary but not wrong
    INFO_GATHERED: 0.3        # unnecessary
    WRONG_TOOL: 0.0           # failure
    HALLUCINATED_TOOL: 0.0    # failure
    NO_ACTION: 0.0            # failure

# Ambiguous scenario
- id: hard_implicit:before_weekend
  prompt: "I need to finish this report before the weekend, remind me"
  scoring:
    TOOL_CALLED: 0.8          # reasonable guess
    CLARIFICATION_ASKED: 1.0  # ideal behavior
    INFO_GATHERED: 0.7        # smart but incomplete
    WRONG_TOOL: 0.0
    HALLUCINATED_TOOL: 0.0
    NO_ACTION: 0.0
```

**Layer 3: Parameter Validation (deterministic, only when TOOL_CALLED)**

Existing assertion checks (`has_timing`, `is_recurring`, `staggered_timing`) run only when the behavioral classifier returns `TOOL_CALLED`. This prevents false failures from clarification responses.

### Why NOT LLM-as-Judge

The project context makes this clear:

1. **25 scenarios, not 2500.** You can read every transcript. LLM-as-judge scales human review -- but there is nothing to scale here.
2. **Non-deterministic grading.** The whole point of v1.1 is to fix unreliable scoring. Adding a stochastic grader makes things worse.
3. **Cost.** Even with Haiku as judge, 25 scenarios x 6 variants x 5 reps x $0.003 = $2.25 per run just for grading. The experiment itself costs ~$0.50.
4. **Debugging opacity.** When an LLM judge gives a score, you cannot deterministically explain why. With behavioral classification, you can point to the exact rule that fired.

LLM-as-judge makes sense for: subjective quality (tone, helpfulness), open-ended responses, 1000+ scenarios. None of these apply here.

## Batch Review Workflow Details

### The Problem

v1.0 had two review modes, both broken:
1. **LangSmith UI:** Shows tool call names and pass/fail, but response text was discarded. Can't see what the agent actually said.
2. **Re-run with probe script:** `eval_probe.py` re-runs scenarios and prints full responses. But re-running is expensive and non-deterministic -- you see a different response each time.

### The Solution: Capture Once, Review Later

**During eval run:**
1. Serialize full response (text + tool calls + usage) to JSONL
2. Run deterministic evaluators and append scores
3. Each JSONL line is self-contained: scenario, variant, prompt, response, scores

**After eval run:**
1. Open JSONL in Claude Code or review script
2. Filter to failures or specific scenarios
3. Read actual agent responses
4. Decide if failure is eval bug or model bug
5. Update evaluator or scenario accordingly

### JSONL Record Format

```json
{
  "timestamp": "2026-02-20T10:00:00Z",
  "experiment_id": "v1.1-run-001",
  "scenario_id": "hard_ambiguous:vague_delay",
  "variant": "baseline",
  "prompt": "remind me about the meeting in a bit",
  "response": {
    "text": "how long is 'a bit'? 10 minutes? an hour?",
    "tool_calls": [],
    "content_blocks": [{"type": "text", "text": "how long is..."}]
  },
  "usage": {"input_tokens": 1234, "output_tokens": 56, "total_tokens": 1290},
  "eval": {
    "behavior": "CLARIFICATION_ASKED",
    "score": 0.8,
    "tool_selection": null,
    "parameter_quality": null,
    "assertions_passed": [],
    "assertions_failed": [],
    "passed": true
  }
}
```

## Experiment Isolation Details

### The Zero-Persona Problem

v1.0 used the full Joi persona for all eval runs. This created confounds:
- Persona says "call recall() first" but eval lacks recall tool
- Persona has personality traits that affect tool selection
- Persona references tools that don't exist in some variants

### Zero-Persona Design

A minimal system prompt that:
1. Describes available tools factually (no personality)
2. Provides current timestamp
3. Gives minimal behavioral guidance ("help the user with their request")
4. Does NOT reference any tools by name (tool descriptions are in the schema)
5. Does NOT include personality, memory instructions, or conversation rules

```
You are a task management assistant. Use the provided tools to help users manage
their schedules and reminders. If the user's request is ambiguous, ask for
clarification.

Current time: 2026-02-20 10:00 UTC
```

This isolates the variable under test (tool interface design) from the confound (persona-driven behavior). Each variant still has its own tool descriptions -- those ARE the experimental variable.

### Full-Persona Mode (Separate Experiment)

After zero-persona establishes tool interface effects, a second experiment adds the persona back to measure interaction effects. But this is v1.2 scope -- v1.1 needs clean data first.

## Scoring Clarification as Valid

### The Core Insight

From the failure analysis: "Eval rewards guessing, punishes precision." When "remind me about the meeting in a bit" has no clear timing, guessing 5 minutes is rewarded (PASS) while asking "how long is 'a bit'?" is punished (FAIL).

### Implementation

Add `ambiguity` field to scenario YAML:

```yaml
- id: hard_ambiguous:vague_delay
  prompt: "remind me about the meeting in a bit"
  ambiguity: timing
  scoring:
    TOOL_CALLED: 0.7
    CLARIFICATION_ASKED: 1.0
```

The behavioral classifier detects clarification via:
1. Response text contains `?` (question mark)
2. No scheduling tool was called, OR scheduling tool was called alongside a question
3. Response text length > 10 characters (filters out empty/error responses)

This is simple, deterministic, and debuggable.

## Single-Turn Eval Best Practices

Based on research and v1.0 lessons:

### Good Single-Turn Scenarios

1. **Unambiguous intent + clear timing:** "remind me to call mom in 5 min" -- only one correct answer exists
2. **Negative boundary:** "I forgot to call mom yesterday" -- should NOT trigger a tool
3. **Hard negative boundary:** "I should probably set a reminder at some point" -- hedging language, should NOT trigger
4. **Multi-part with clear components:** "remind me at 3pm and 5pm" -- two distinct, unambiguous items

### Bad Single-Turn Scenarios (Require Redesign for v1.1)

1. **Ambiguous timing without scoring rules:** "remind me before the weekend" -- if scored as strict pass/fail, penalizes correct clarification behavior
2. **Context-dependent:** "do the usual morning check on me" -- requires memory of past behavior, single-turn cannot provide this context
3. **Time-sensitive:** anything referencing "today" or "tonight" without fixed timestamps

### Design Rules

1. Every scenario must have at least one valid outcome achievable in a single turn
2. If clarification is a valid response, the scenario MUST have `ambiguity` tag and scoring rules for `CLARIFICATION_ASKED`
3. Scenarios should be self-contained -- no external context needed (no "the usual", no "that meeting")
4. Use fixed timestamps, never `datetime.now()`
5. Each scenario should test ONE thing: tool selection OR parameter extraction OR routing OR ambiguity handling -- not all at once

## MVP Recommendation

Prioritize for v1.1 (in order):

1. **Fix response serialization** -- Low complexity, blocks everything else. Without full response text, no batch review is possible.
2. **Fix `_check_has_timing` evaluator bug** -- Low complexity, eliminates 20+ false failures from v1.0 data.
3. **Fix persona-tool mismatch / zero-persona mode** -- Med complexity, eliminates the `recall` hallucination confound.
4. **JSONL capture log** -- Med complexity, enables batch review workflow. This is the foundation for "capture once, review later."
5. **Behavioral classification evaluator** -- Med complexity, replaces binary pass/fail with nuanced scoring. Directly addresses "eval rewards guessing."
6. **Review script** -- Med complexity, makes JSONL data human-readable.
7. **Ambiguity tags + clarification scoring** -- Low complexity on top of behavioral classifier. Fixes the 3 most broken scenarios.

Defer to v1.2:
- **Diff mode between runs** -- useful but not blocking. Can manually compare JSONL files.
- **Scenario difficulty calibration** -- nice-to-have, not blocking trustworthy results.
- **Multiple valid outcomes per scenario** -- behavioral classifier + ambiguity tags handle 90% of this need.
- **Full-persona re-test** -- needs clean zero-persona data first.

## Sources

### HIGH Confidence
- `docs/eval-failure-analysis.md` -- Primary source for v1.0 bugs and systemic issues. First-hand evidence from 960+ LLM calls.
- `tests/eval/evaluators.py` -- Existing evaluator code, verified bugs at lines 61-72 (`_check_has_timing`).
- `tests/eval/test_tasks.py` -- Existing test structure, serialization bug at line 34.
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- Authoritative guidance on response capture ("capture the full messages array"), transcript review ("you won't know if graders are working unless you read transcripts"), experiment isolation ("each trial should be isolated, starts fresh"), and evaluator types (code-based vs model-based vs human).
- [LangChain AgentEvals](https://github.com/langchain-ai/agentevals) -- Trajectory match modes (strict, unordered, subset, superset), tool call scoring patterns with configurable `tool_args_match_mode`.
- [LangSmith Trajectory Evals](https://docs.langchain.com/langsmith/trajectory-evals) -- Data capture format for tool calls, partial match scoring via graduated matching modes.

### MEDIUM Confidence
- [LangChain: Evaluating Deep Agents](https://blog.langchain.com/evaluating-deep-agents-our-learnings/) -- "Deep agents require bespoke test logic for each datapoint." Three capture categories: trajectory, final response, other state. Emphasis on fresh environments per trial.
- [EvalScope Function Calling Guide](https://evalscope.readthedocs.io/en/latest/best_practice/general_fc.html) -- Tool call F1 scoring (`tool_call_f1`, `schema_accuracy`), dual verification (should-call + correct-params), negative sample design.
- [Confident AI: Agent Evaluation Guide](https://www.confident-ai.com/blog/definitive-ai-agent-evaluation-guide) -- Behavioral classification patterns, dual verification of decision accuracy and parameter validity.

### LOW Confidence
- General web search results on batch annotation workflows -- mostly enterprise-focused (Labelbox, Scale AI) patterns not applicable to solo developer with 25 scenarios.
- "80% automated + 20% human review" ratio cited across multiple sources but without rigorous backing for small eval sets.
