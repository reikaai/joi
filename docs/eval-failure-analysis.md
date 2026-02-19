# Eval Pipeline Failure Analysis — Hard Scenarios

Post-mortem on Milestone 1 eval results. We re-ran 5 key "failing" scenarios with full response capture and found that **most failures are eval design issues, not model failures**.

## Critical Bug: Response Text Discarded

`test_tasks.py:34` — `"content": response.content if isinstance(response.content, str) else ""` — when Haiku returns tool calls + text, content is a list → gets serialized as `""`. `t.log_outputs` only logs `tool_call_names` and `call_count`. **We never stored what Haiku actually said.** This made it impossible to diagnose failures without re-running.

## Scenario-by-Scenario Findings

### usual_morning: "do the usual morning check on me"

| Variant | What Haiku did | Eval said |
|---|---|---|
| baseline | `recall({})` — tries to look up what "the usual" means | FAIL |
| applike | `reminders_create(schedule='0 8 * * *')` + text "I'll set up a morning check-in" | FAIL |

**Problems:**
1. Baseline `recall` is a reasonable first step in a multi-turn flow — look up what "the usual" is, then schedule.
2. Applike actually SUCCEEDS — creates a daily 8am reminder. But `_check_has_timing` (evaluators.py:61-72) only checks `delay_seconds` and `when`, not `schedule`. **Evaluator bug** — `is_recurring` checks `schedule` but `has_timing` doesn't.

### before_weekend: "I need to finish this report before the weekend, remind me"

| Variant | What Haiku did | Eval said |
|---|---|---|
| baseline | "you want me to bug you before the weekend ends, or before it starts? what day/time works?" | FAIL |
| applike | `calendar_list_events({})` + "when do you wanna be reminded? tomorrow morning? evening?" | FAIL |

**Problems:**
1. Both responses are **correct behavior** — the prompt is genuinely ambiguous. "Before the weekend" could mean Friday morning, Thursday evening, etc. Asking for clarification is the right call.
2. Applike additionally calls `calendar_list_events` to check the user's schedule — smart info gathering.
3. Eval expects immediate scheduling on turn 1. **Single-turn eval penalizes clarification.**

### vague_delay: "remind me about the meeting in a bit"

| Variant | What Haiku did | Eval said |
|---|---|---|
| baseline | `schedule_task(delay_seconds=300)` — guesses 5 min | PASS |
| applike | `calendar_list_events({})` + "how long is 'a bit'? 10 minutes? an hour?" | FAIL |

**Problems:**
1. Baseline "passes" by **guessing** 5 minutes. Is this actually correct? "In a bit" could mean 15 min, 30 min, 1 hour. The eval rewards guessing.
2. Applike does TWO reasonable things: (a) looks up "the meeting" in calendar to get context, (b) asks how long "a bit" is. This is better UX behavior.
3. **Eval rewards trigger-happiness, punishes precision.**

### implicit_recurring: "I keep forgetting to take my vitamins"

| Variant | What Haiku did | Eval said |
|---|---|---|
| baseline | `run_code(remember("forgets to take vitamins regularly"))` | FAIL |
| applike | "what schedule do you want? daily? every morning?" — asks for clarification | FAIL |

**Problems:**
1. Baseline stores a memory note about the user's vitamin habit. This is a valid first step — remember the need, then set up a reminder in a follow-up.
2. Applike asks whether daily or morning — reasonable because the prompt gives NO timing info. The human also struggles: is this Calendar or Reminders? Daily or once?
3. Eval expects immediate `schedule_task` with `recurring=True`, but the prompt never specifies when/how often.

### mixed_topic: "What about the weather? Also set a reminder for 5pm to call the dentist"

| Variant | What Haiku did | Eval said |
|---|---|---|
| applike | `reminders_create(schedule='0 17 * * *')` + notices "5pm was hours ago, you mean tomorrow?" | FAIL |

**Problems:**
1. Haiku correctly identifies the time issue (it's 9:38pm, 5pm already passed) and asks about tomorrow.
2. Routes to `reminders_create` instead of `calendar_create_event` because the prompt says "set a **reminder**" — literal word match to tool name "Reminders". This is a **naming trap**: humans say "remind me" for both one-time and recurring.
3. Creates cron `0 17 * * *` (daily 5pm) because `reminders_create`'s only timing param is `schedule` (cron). The tool design forces recurring behavior even for one-time requests routed here.
4. `_check_has_timing` doesn't check `schedule` param → evaluator bug on top of routing issue.

### `recall` tool calls — persona-tool mismatch, not hallucination

Baseline produces `recall({})` calls, but `recall` is NOT in the baseline tool set (`schedule_task`, `list_tasks`, `update_task`, `run_code`). Investigation:

1. **Real agent** has `recall` and `remember` as standalone LangChain tools (`memory.py:20`, `memory.py:11`) backed by Mem0
2. **Persona** (shared with real agent) says: `"Tools: remember(), recall()"`, `"First message → call recall() first. Silently."`, `"direct tool call is simpler"` than wrapping in `run_code`
3. **Eval baseline** strips memory tools but keeps the persona instructions about them
4. Haiku reads persona → obeys the rules → generates `recall` call → but it's not in the bound schema

This is **not** a hallucination or built-in tool. It's Haiku correctly following persona instructions that reference tools that aren't available in the eval context. The persona-tool mismatch inflates "wrong tool" failure counts: every `recall` call is actually Haiku doing what the persona told it to do.

**Same applies to** `run_code(remember(...))` calls — persona says `"run_code sandboxed Python with remember(), recall()"` and `"USE for: batch memory ops"`. Haiku uses `run_code` as a fallback path to reach `remember()` since direct `recall` doesn't work.

**Fix:** Either include `recall`/`remember` mock tools in the eval tool set, or strip memory instructions from the eval persona.

## Systemic Issues

### 1. Single-turn eval for multi-turn behavior
The eval sends one message and expects immediate scheduling. But for ambiguous inputs, a good agent should:
1. Gather context (recall memory, list calendar)
2. Ask clarification ("when exactly?")
3. THEN schedule

The eval can't see steps 2-3. It marks step 1 as failure.

### 2. Eval rewards guessing, punishes precision
Baseline "passes" vague_delay by guessing `delay_seconds=300`. Applike "fails" by asking "how long is a bit?" The eval prefers a wrong-but-confident answer over a correct-but-cautious one.

### 3. `has_timing` evaluator bug
`_check_has_timing` (evaluators.py:61-72) checks `delay_seconds` and `when` but NOT `schedule`. The `reminders_create` tool uses `schedule` for cron expressions. This causes false failures on:
- `hard_multi:onetime_plus_recurring` (applike) — 10/10 false FAIL
- `hard_multi:two_different_times` (applike) — 10/10 false FAIL
- `hard_distractor:mixed_topic` (applike) — partial false FAILs
- `usual_morning` (applike) — false FAIL

### 4. Response text not stored
`_serialize_response` discards text when `response.content` is a list (which it always is when tool calls are present). LangSmith `t.log_outputs` only logs tool names/counts. **We can't diagnose any failure without re-running the scenario.**

### 5. "reminder" → Reminders name trap
Users say "remind me" for both one-time and recurring tasks. The applike tool named `reminders_create` captures this word, causing one-time requests to route to the recurring tool. This is a tool naming design problem, not a model capability problem.

## Impact on ADR Conclusions

The ADR concluded: "REJECT app-like variant. Routing tax on ambiguous inputs (-36.7%, p=0.006)."

**This conclusion needs revision:**
- The 36.7% gap on `hard_ambiguous` is real — but it measures "willingness to guess" not "accuracy"
- Applike's lower score = more clarification questions + more info gathering
- Baseline's higher score = more blind guessing (5-min delay for "in a bit")
- `hard_multi` 100% baseline vs 0% applike was entirely evaluator bug (all 20 applike runs were correct)
- `hard_implicit` floor effect was both variants asking clarification (correct) not failing

The finding "consolidated tools > decomposed tools" may still hold for different reasons (naming trap, forced-recurring routing), but the statistical evidence is weaker than reported.

## Recommendations

1. **Fix `_serialize_response`** — always store full content (serialize list content properly)
2. **Fix `_check_has_timing`** — add `args.get("schedule")` check
3. **Log response text to LangSmith** — `t.log_outputs({"text": ..., "tool_call_names": ...})`
4. **Add multi-turn eval** — allow 2-3 turns for info gathering before judging
5. **Score clarification as valid** — "asks for timing" should not be a failure
6. **Reconsider "Reminders" naming** — the word "reminder" in user prompts routes to recurring tool
7. **Re-run Pivot 2 with fixes** — the statistical comparison needs clean data
