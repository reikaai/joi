# Pitfalls Research

**Domain:** AI Agent Tool Interface Evaluation ("Apps vs Tools" Experiment)
**Researched:** 2026-02-19
**Confidence:** HIGH (multi-source verification across Anthropic engineering docs, academic papers, and practitioner reports)

## Critical Pitfalls

### Pitfall 1: Confounding Tool Design Changes with Prompt Wording Effects

**What goes wrong:**
You redesign `schedule_task` into a "Calendar" app-like tool, see improved success rates, and conclude the "app metaphor" works. But the improvement came from better tool descriptions, clearer parameter names, or more examples in the docstring -- not the metaphor itself. Research shows LLMs exhibit up to 463% performance swings from prompt rewording alone (Llama-2-70B-chat: 9.4% to 54.9% accuracy from 12 rephrasings of the same instruction). When you change the tool interface, you simultaneously change the tool name, description, parameter names, description text, and schema structure. Every one of these is a variable.

**Why it happens:**
The "apps vs tools" comparison is inherently multi-variable. Moving from `schedule_task(title, description, when, delay_seconds, recurring)` to a "Calendar" app with `add_event(what, when, recurring)` changes at minimum: (a) tool name/metaphor, (b) parameter count, (c) parameter naming convention, (d) description prose, (e) schema complexity. You cannot isolate which change drove the result.

**How to avoid:**
Design the experiment as a series of incremental, single-variable changes:
1. **Baseline:** Current `schedule_task` as-is
2. **Rename only:** Same schema, rename to `calendar_add_event` -- tests the naming/metaphor hypothesis
3. **Simplify params:** Same name, reduce parameter count -- tests complexity reduction
4. **Improve descriptions:** Same schema, rewrite descriptions only -- tests description quality
5. **Full "app" design:** Everything combined -- gives the final number

Compare each step against baseline. If step 2 (rename only) explains 80% of the gain, the metaphor matters. If step 3 (simplify) explains it, then it was complexity reduction, not the app metaphor.

**Warning signs:**
- You only test "before" and "after" with no intermediate variants
- Results are dramatic (>20% improvement) -- likely multi-variable confound
- You cannot articulate which specific change drove which specific improvement

**Phase to address:** Eval Framework Design (Phase 1)

---

### Pitfall 2: Evaluation Set Too Small or Too Narrow to Draw Conclusions

**What goes wrong:**
You test with 10-20 hand-crafted scenarios, see 80% vs 60% success rates, declare victory for the new interface. But with n=20, the 95% confidence interval for an 80% success rate is [56%, 94%]. Your 60% baseline falls squarely within it. You have measured noise, not signal. Worse, correlated LLM outputs mean your effective sample size is even smaller than the nominal count -- semantically similar prompts may only provide the statistical power of a few independent samples.

**Why it happens:**
LLM evaluations feel expensive: each test case requires prompt construction, tool execution, and grading (often manual). Teams stop at "feels like enough." Additionally, LLM stochasticity means even the same prompt produces different results across runs, requiring multiple trials per test case (pass@k).

**How to avoid:**
- Use power analysis upfront. For detecting a 20% improvement (60% to 80%) at p<0.05 with 80% power, you need approximately 82 independent test cases per variant (McNemar's test for paired comparisons).
- For each test case, run 3-5 trials to account for LLM stochasticity. Report both pass@1 (single attempt) and pass@5 (at least one success in 5 attempts).
- Ensure semantic diversity: "remind me to check the oven in 5 minutes" and "set a 5-minute oven reminder" are NOT independent test cases. Cluster by intent and count clusters, not individual prompts.
- Use Joi's actual conversation logs to mine real user intents rather than hand-crafting synthetic scenarios.

**Warning signs:**
- Fewer than 50 test cases per variant
- No reported confidence intervals
- Test cases are all slight rephrasings of the same 5 intents
- No multi-trial runs (only pass@1 reported)
- Results are "close" (within 15%) but declared significant

**Phase to address:** Eval Framework Design (Phase 1)

---

### Pitfall 3: Optimizing Metrics That Don't Map to User Value

**What goes wrong:**
You measure "tool call accuracy" (did the LLM select the right tool with correct parameters?) and optimize for it. The "Calendar" tool wins on accuracy because it has fewer parameters to get wrong. But in production, the user experience degrades because the simplified tool can't express complex scheduling scenarios that `schedule_task` handled. Or conversely: the new tool's accuracy is high but its token cost is 2x, making the agent noticeably slower.

**Why it happens:**
Tool call accuracy is easy to measure and satisfying to optimize. Real user value -- "did the user's intent get fulfilled end-to-end?" -- requires evaluating the full pipeline: intent understanding, tool selection, parameter extraction, execution, and response quality. Teams default to the easiest metric.

**How to avoid:**
Define a metric hierarchy before starting:
1. **Primary:** Task completion rate (did the user's stated intent actually happen? Verified by checking task store state)
2. **Secondary:** Token efficiency (total tokens consumed for the full interaction, including retries)
3. **Secondary:** First-attempt success rate (no retries needed)
4. **Tertiary:** Tool selection accuracy (chose the right tool)
5. **Tertiary:** Parameter accuracy (correct parameters on first try)

Never let tertiary metrics override primary metrics. A tool design that scores 95% on parameter accuracy but only 70% on task completion is worse than one that scores 80% on parameter accuracy but 90% on task completion.

**Warning signs:**
- Evaluation only measures tool call correctness, not end-to-end task completion
- No measurement of what happens after the tool executes (was the result correct?)
- Token cost is not part of the evaluation
- You're celebrating parameter accuracy improvements while ignoring that some scenarios are now impossible to express

**Phase to address:** Eval Framework Design (Phase 1)

---

### Pitfall 4: The "App Metaphor" Smuggles in Capability Reduction

**What goes wrong:**
The move from programmatic tools to "app-like" tools feels like an improvement because it reduces the parameter space. But you've secretly dropped capabilities. The current `schedule_task` supports: one-shot by ISO datetime, one-shot by delay_seconds, recurring by cron expression, with title and description separation. If "Calendar.add_event" simplifies to `what` + `when` + `recurring`, you've lost: (a) explicit delay_seconds for relative scheduling, (b) title/description separation (important for task context messages), (c) possibly cron expression support. The eval shows "improvement" because the reduced tool is easier to call correctly -- on the scenarios that still work.

**Why it happens:**
Simplification bias. The "app metaphor" implicitly encourages fewer, higher-level operations. This is sometimes good (less room for error) but sometimes bad (less expressiveness). The risk is acute when the existing interface evolved to handle real edge cases that synthetic eval scenarios don't cover.

**How to avoid:**
- Before redesigning, audit every parameter and capability of the current tools. Document which real user scenarios depend on each parameter. Use Joi's actual conversation history.
- Define "capability parity" as a hard requirement: the new interface must handle every scenario the old one handles.
- Include capability coverage in the eval: test cases must explicitly cover features that exist in the old design but might be missing from the new one.
- If you intentionally drop capabilities, document it as a conscious tradeoff, not an accidental omission.

**Warning signs:**
- The new design has fewer parameters but nobody checked which scenarios break
- Eval test cases only cover the "happy path" -- basic scheduling
- Real user scenarios from conversation history are not part of the eval set
- "We can always add those features later" -- the deferred features were load-bearing

**Phase to address:** Tool Redesign (Phase 2), with audit in Phase 1

---

### Pitfall 5: Token Bloat from "App-Like" Tool Descriptions Degrades Overall Agent Performance

**What goes wrong:**
"App-like" tools tend toward richer descriptions -- the Calendar "app" might include usage patterns, examples, state management docs, and relationship descriptions. Research shows MCP tool definitions can consume 14K+ tokens per server (20 tools), and Claude's tool selection accuracy degrades as context grows (0.24ms latency per token, attention interference from irrelevant definitions). If your "app" tools add 30% more description tokens, you've degraded performance on everything else the agent does, not just scheduling.

**Why it happens:**
The "app" metaphor encourages treating tool descriptions like documentation -- comprehensive, with examples and usage patterns. This is good for human developers but bad for LLMs in context-constrained settings. Anthropic's own guidance says to build "a few thoughtful tools" but also says to "make implicit context explicit." These goals conflict when the tool set grows.

**How to avoid:**
- Measure total tool description token count before and after redesign. Set a budget: new design must not exceed current token count by more than 10%.
- Use Anthropic's `defer_loading: true` / Tool Search Tool if the tool set grows beyond ~10 tools.
- Test agent performance on NON-scheduling tasks with the new tool definitions loaded. If unrelated task performance drops, your descriptions are too heavy.
- Prefer schema clarity (good parameter names, types, enums) over prose description. `when: str | Field(description="ISO datetime or cron")` is better than a paragraph explaining scheduling.

**Warning signs:**
- Tool descriptions exceed 500 tokens per tool
- Agent becomes slower or less accurate on unrelated tasks after tool change
- You added examples/usage patterns to tool descriptions (high token cost, marginal benefit for Claude)
- Total tool definition overhead exceeds 5% of context window

**Phase to address:** Tool Redesign (Phase 2)

---

### Pitfall 6: Evaluating on Synthetic Scenarios Instead of Real User Behavior

**What goes wrong:**
You create test cases like "schedule a meeting for tomorrow at 3pm" and "remind me to call mom." These are clean, unambiguous intents. Real Joi usage (from conversation logs) includes: ambiguous timing ("later today"), multi-step sequences ("count to 3 with 5s pauses"), context-dependent scheduling ("after the movie finishes"), and corrections ("actually make it 4pm not 3pm"). The eval shows improvement on synthetic cases but the agent performs the same or worse on real cases.

**Why it happens:**
Synthetic test cases reflect what developers think users say, not what users actually say. Anthropic's eval guide explicitly warns: "Everything the grader checks should be clear from the task description." But real user messages are inherently unclear, and the tool interface must handle that ambiguity.

**How to avoid:**
- Mine Joi's actual Telegram conversation history for real scheduling-related messages. Extract at least 50 unique, real intents.
- Categorize by difficulty: simple ("remind me in 5 min"), moderate ("every weekday at 8am"), complex ("check if the download finished, if not retry in 10 minutes"), ambiguous ("sometime this afternoon").
- Weight the eval set toward the distribution of real usage, not uniform across categories.
- Include at least 20% "adversarial" cases: typos, ambiguous timing, contradictory instructions, corrections mid-flow.

**Warning signs:**
- All test cases are grammatically perfect, single-intent sentences
- No test cases derived from actual Joi usage
- Edge cases (cron, delay_seconds, multi-step) are underrepresented
- No ambiguous or correction-based scenarios

**Phase to address:** Eval Dataset Creation (Phase 1)

---

### Pitfall 7: Breaking Existing Task System Workflows During Migration

**What goes wrong:**
Research shows tool versioning causes 60% of production agent failures. Joi's task system is live -- background tasks, recurring crons, the notifier, HITL interrupts all depend on the current `schedule_task`/`update_task`/`list_tasks` interface. Changing tool names, parameter shapes, or return value formats breaks: (a) in-flight scheduled tasks that reference old tool schemas, (b) the system prompt examples that teach the agent how to use tools, (c) the `_task_context_message` format, (d) the `MUTATION_TOOLS` set, (e) any mem0 memories that reference old tool names.

**Why it happens:**
Tool interfaces are APIs. They have downstream consumers you don't always see. In Joi's case, the task system is deeply integrated: `graph.py` imports task tools, the notifier checks task states, background task threads send context messages that reference tool behavior. Changing the tool surface is not just a tool change -- it's a system change.

**How to avoid:**
- Run the experiment with ADDITIONAL tools, not REPLACEMENT tools. Add `calendar_add_event` alongside `schedule_task`. Compare which one the agent chooses and how well it performs.
- Only replace after the experiment concludes with clear results.
- If replacing, use a migration phase: keep old tools as deprecated aliases that delegate to new implementations.
- Test the full lifecycle: create task, list tasks, update task, cancel task, recurring task, notifier delivery. Not just creation.

**Warning signs:**
- You deleted old tools before proving new ones are better
- Test coverage only covers tool creation, not the full task lifecycle
- System prompt wasn't updated to match new tool names
- Background tasks created with old interface fail silently with new interface

**Phase to address:** Migration Strategy (Phase 3)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode eval scenarios | Fast eval setup | Brittle, doesn't catch real-world edge cases | Never for final evaluation; OK for initial smoke tests |
| Skip multi-trial runs | 3-5x fewer API calls | Can't distinguish signal from LLM stochasticity | Only during rapid prototyping, never for comparison |
| Evaluate tool selection only, not end-to-end | Simple grading | Misses actual user impact | Never as primary metric |
| Replace tools without alias period | Clean codebase | Breaks in-flight tasks and agent memories | Never in a live system |
| Use LLM-as-judge without calibration | No human grading needed | Systematic bias, false positives | OK for ranking, never for absolute measurements |

## Integration Gotchas

Common mistakes when connecting to the existing Joi ecosystem during the experiment.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Task Store (`tasks/store.py`) | New tool writes different field shapes, breaks notifier reads | Keep TaskState model unchanged; adapt at tool level |
| System Prompt | Forget to update tool usage examples after renaming | Parameterize examples or test system prompt compatibility |
| `MUTATION_TOOLS` set | New tool names not added, HITL interrupts don't fire | Audit `tools.py:MUTATION_TOOLS` whenever tool names change |
| `_task_context_message` | New tool generates context messages the background agent doesn't understand | Test background task execution, not just creation |
| Mem0 memories | Old memories reference "schedule_task" by name, agent confused by mismatch | Either migrate memories or ensure backward-compatible tool names |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Verbose "app" tool descriptions | Works with 3 tools, degrades with 10+ | Token budget per tool (<500 tokens) | >10 tools or >5K total description tokens |
| Running eval with temperature=0 only | Consistent results, false confidence | Test at temperature=0 and temperature=0.7 | Any production deployment (temp>0) |
| Evaluating with current Claude model only | Works on Sonnet 4, breaks on model update | Test on 2+ model versions | Next model release |
| Loading all tool variants simultaneously for A/B | Doubles context overhead | Load only one variant per session | >20 total tools loaded |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| App-like tool requires structured input the user doesn't provide | Agent asks clarifying questions = slower UX | Tool must handle ambiguous input and resolve internally |
| Over-consolidated tool with too many internal modes | Agent picks wrong mode, user gets unexpected behavior | Each mode should be testable independently |
| Tool returns human-friendly text but agent needs structured data | Agent can't chain tool results for multi-step tasks | Return structured data with human-readable summary |
| Simplified tool drops "delay_seconds" capability | User says "in 5 minutes" and agent can't express it | Audit every parameter against real usage before removing |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Eval framework:** Often missing multi-trial runs -- verify each test case runs 3+ times
- [ ] **Tool redesign:** Often missing capability parity check -- verify every old parameter maps to new interface
- [ ] **A/B comparison:** Often missing confidence intervals -- verify statistical significance is computed
- [ ] **Migration:** Often missing background task lifecycle test -- verify create/list/update/cancel/notify all work
- [ ] **System prompt:** Often missing updated examples -- verify system prompt references correct tool names
- [ ] **Token budget:** Often missing measurement -- verify total tool description tokens before and after
- [ ] **Real user scenarios:** Often missing from eval set -- verify at least 30% of test cases from real Joi conversations
- [ ] **Non-scheduling regression:** Often not tested -- verify agent performance on media/memory tasks is unchanged

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Confounded multi-variable results | MEDIUM | Re-run with isolated variables; design A/A test to establish baseline variance |
| Too-small eval set | LOW | Add more test cases; existing results are still valid data points |
| Wrong metrics optimized | HIGH | Re-evaluate with correct metrics; may need to undo tool changes |
| Capability silently dropped | MEDIUM | Add missing capabilities to new design; re-run affected eval scenarios |
| Token bloat degraded agent | LOW | Trim descriptions, add `defer_loading`; immediate improvement |
| Synthetic-only eval | MEDIUM | Mine real conversations; re-run eval with mixed real+synthetic set |
| Broke live task system | HIGH | Rollback to old tools; debug and fix new tools separately; migration alias pattern |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Multi-variable confounding | Phase 1: Eval Design | Eval plan documents isolated variable tests |
| Small eval set | Phase 1: Eval Design | Power analysis completed; n >= 50 independent cases |
| Wrong metrics | Phase 1: Eval Design | Metric hierarchy documented with primary = task completion |
| Capability reduction | Phase 1: Audit + Phase 2: Redesign | Capability parity matrix complete |
| Token bloat | Phase 2: Redesign | Token count before/after measured; budget not exceeded |
| Synthetic-only scenarios | Phase 1: Dataset Creation | >= 30% test cases from real Joi conversations |
| Breaking live system | Phase 3: Migration | Additive deployment (new tools alongside old); full lifecycle test |

## Sources

- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- task design, grading, multi-trial methodology
- [Anthropic: Writing Effective Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) -- tool description best practices, consolidation vs granularity
- [Anthropic: Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) -- Tool Search, defer_loading, token management
- [HoneyHive: Avoiding Common Pitfalls in LLM Evaluation](https://www.honeyhive.ai/post/avoiding-common-pitfalls-in-llm-evaluation) -- statistical rigor, metric decomposition
- [arXiv 2410.19920: Prompt Overfitting in RL-Aligned LLM Agents](https://arxiv.org/html/2410.19920v2) -- prompt format sensitivity, contrastive regularization
- [NAACL 2025: Quantifying LLMs' Sensitivity to Prompt Engineering](https://aclanthology.org/2025.naacl-long.73.pdf) -- 463% accuracy swing from rewording
- [Chroma Research: Context Rot](https://research.trychroma.com/context-rot) -- performance degradation with context length
- [GitHub: Claude Code MCP Token Bloat](https://github.com/anthropics/claude-code/issues/3406) -- 10-20K token overhead from tool definitions
- [Maxim: A/B Testing Strategies for AI Agents](https://www.getmaxim.ai/articles/a-b-testing-strategies-for-ai-agents-how-to-optimize-performance-and-quality/) -- sample size, confounding variables
- [arXiv 2503.11069: API Agents vs GUI Agents](https://arxiv.org/html/2503.11069v1) -- paradigm comparison challenges
- [MCP Token Bloat Issue #1576](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576) -- schema redundancy in tool definitions
- [Berkeley Function Calling Leaderboard V4](https://gorilla.cs.berkeley.edu/leaderboard.html) -- format sensitivity test cases

---
*Pitfalls research for: AI Agent Tool Interface Evaluation ("Apps vs Tools")*
*Researched: 2026-02-19*
