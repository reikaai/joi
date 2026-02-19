# Domain Pitfalls: Rebuilding a Broken Agent Eval Pipeline

**Domain:** Agent evaluation pipeline rebuild (post-mortem informed)
**Researched:** 2026-02-20
**Context:** v1.0 eval produced statistically significant results (p=0.006) that were partially based on 5 systemic bugs. The REJECT decision for app-like interfaces may need revision. This document catalogs pitfalls specific to rebuilding an eval pipeline after trust has been broken.

---

## Critical Pitfalls

Mistakes that invalidated v1.0 results or would invalidate v2.0 results if repeated. Each is paired with the specific v1.0 failure it maps to.

---

### Pitfall 1: Response Data Silently Discarded by Type Coercion

**v1.0 failure:** `_serialize_response` used `response.content if isinstance(response.content, str) else ""` -- when Haiku returns tool calls + text, `content` is a list of dicts, not a string. The entire response text was replaced with `""`. LangSmith `t.log_outputs` only logged `tool_call_names` and `call_count`. The actual words the agent spoke were lost forever.

**What goes wrong:** Response serialization code assumes a fixed type shape that doesn't match reality. LLM APIs return polymorphic content fields -- sometimes a string, sometimes a list of blocks (text + tool_use). A simple `isinstance` check silently drops data instead of raising an error. You end up with an eval that can tell you WHAT tools were called but not WHAT the agent said, making failure diagnosis impossible without re-running (and spending money).

**Why it happens:** LangChain's `AIMessage.content` type is `Union[str, list[dict]]`. When only tool calls are present, some providers return a string; when text accompanies tool calls, it becomes a list. Developers write serialization for the common case and never see the data loss because the eval still "works" -- it just loses half the information.

**Consequences:**
- Cannot distinguish "agent asked a clarification question" from "agent said nothing" -- both show as `""`
- Cannot diagnose failures without re-running ($$ and different LLM sampling = non-reproducible)
- Failure analysis becomes impossible at scale -- you must re-run every suspicious result
- v1.0 required a dedicated `eval_probe.py` script and ~$2 of re-runs just to understand 5 scenarios

**Prevention:**
1. **Serialize defensively:** Always handle the union type. Extract text from list content.
   ```python
   if isinstance(content, list):
       text = " ".join(c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text")
   else:
       text = content or ""
   ```
2. **Assert completeness:** Add a post-serialization check that response text is non-empty when the LLM produced output tokens.
3. **Log EVERYTHING:** Store raw `response.content` (whatever type it is) alongside parsed fields. Disk is cheap; re-runs are not.
4. **Smoke test serialization:** Before any batch run, serialize 1 response manually and verify all fields are present. Print it. Look at it.

**Detection (warning signs you have this bug):**
- Response text column is empty or `""` for most/all rows
- You can see tool call names but not what the agent said alongside them
- Failure diagnosis requires re-running scenarios
- `output_tokens > 0` but stored text is empty

**Phase to address:** Phase 1 (eval infrastructure rebuild) -- fix before running ANY experiments.

---

### Pitfall 2: Evaluator Bug in Parameter Checking (Incomplete Coverage)

**v1.0 failure:** `_check_has_timing` (evaluators.py:61-72) checked `delay_seconds` and `when` but NOT `schedule` (cron expressions). The `reminders_create` tool uses `schedule` for its timing parameter. This caused 100% false FAIL on `hard_multi:onetime_plus_recurring` and `hard_multi:two_different_times` -- all 20 applike runs were actually correct but marked as failures.

**What goes wrong:** A deterministic evaluator checks for expected parameter names, but the tool interface has multiple valid ways to express the same concept. When a new tool variant uses a different parameter name for timing (e.g., `schedule` instead of `when` or `delay_seconds`), the evaluator silently marks correct responses as failures. The bug is invisible in aggregate statistics because it looks like a genuine performance difference.

**Why it happens:** Evaluators are written against one tool interface and tested against that interface. When a new variant introduces different parameter names, nobody updates the evaluator to handle the new names. The evaluator "works" (no crashes, no errors) -- it just produces wrong answers. This is the eval equivalent of a silent data corruption bug.

**Consequences:**
- v1.0: 20 runs scored as FAIL that were actually PASS -- a 100% false negative rate on 2 scenario categories
- The aggregate `hard_multi` category showed "baseline 100% vs applike 0%" -- entirely an evaluator artifact
- This fake signal contributed to the statistically significant p=0.006 result
- The REJECT decision was partially based on fabricated evidence

**Prevention:**
1. **Evaluator-variant co-testing:** Every tool variant must have a unit test that feeds a known-correct response through the evaluator and asserts PASS. If you add a variant with `schedule` instead of `when`, there must be a test proving the evaluator handles `schedule`.
2. **Exhaustive parameter coverage:** For timing checks, enumerate ALL parameter names that can carry timing info: `delay_seconds`, `when`, `schedule`, and any future additions. Use a whitelist, not a blacklist.
3. **Golden response tests:** For each scenario x variant, create a "golden" response (hand-crafted correct answer) and assert the evaluator scores it as PASS. If the golden response fails, the evaluator is broken.
4. **Symmetric testing:** For every evaluator assertion, test BOTH directions: (a) correct response scores PASS, (b) incorrect response scores FAIL. v1.0 only tested direction (b) implicitly through live runs.

**Detection (warning signs you have this bug):**
- One variant shows 0% on a category while another shows 100% -- too clean, too perfect
- The 0% variant's responses, when examined manually, look reasonable
- Evaluator logic references specific parameter names from one variant but not others
- Adding a new tool variant without touching evaluator code

**Phase to address:** Phase 1 (eval infrastructure rebuild) -- evaluators must be co-tested with every variant before experiments run.

---

### Pitfall 3: Single-Turn Eval Penalizes Correct Multi-Turn Behavior

**v1.0 failure:** The eval sent one message and expected immediate tool calls. But for ambiguous inputs ("remind me about the meeting in a bit"), a GOOD agent should ask for clarification or gather context first. The eval scored clarification-seeking as FAIL. It literally rewarded guessing (baseline: `delay_seconds=300` for "in a bit" = PASS) and punished precision (applike: "how long is 'a bit'?" = FAIL).

**What goes wrong:** A single-turn eval assumes the correct behavior fits in one response. For agents that handle ambiguity well -- by asking clarifying questions, checking context (memory, calendar), or requesting more information -- the eval cannot observe the multi-step process. It only sees "no tool call on turn 1" and marks it as failure. The eval systematically rewards trigger-happy, overconfident agents and punishes cautious, accurate ones.

**Why it happens:** Multi-turn eval is genuinely harder to build. You need: (a) a conversation simulator or script, (b) a way to mock tool responses, (c) evaluation criteria that span multiple turns, (d) a way to determine when the conversation should end. Single-turn is simple: send prompt, check response, done. Teams default to what's easy.

**Consequences:**
- v1.0: Baseline "passed" `vague_delay` by blindly guessing 5 minutes. Applike "failed" by asking "how long is 'a bit'?" -- the better UX behavior
- The eval rewarded trigger-happiness and punished precision -- the OPPOSITE of what a good personal assistant should do
- `hard_ambiguous` category showed 53.3% baseline vs 16.7% applike -- but the "failures" were actually the applike variant being smarter (asking clarification)
- `hard_implicit` showed 20% baseline vs 5% applike -- both asking clarification, both scored as failure
- The entire "routing tax on ambiguous inputs" finding was actually "applike asks more clarification questions"

**Prevention:**
1. **Distinguish scenario types:** Classify scenarios as "clear intent" (single-turn eval OK) vs "ambiguous intent" (needs multi-turn or different scoring).
2. **Score clarification as valid:** For ambiguous scenarios, "asks clarifying question" should be a PASS, not a FAIL. Add an assertion type `accepts_clarification` that checks if the response contains a question.
3. **Multi-turn eval for ambiguous scenarios:** For scenarios where clarification is the correct first step, script a 2-3 turn conversation: (1) ambiguous user message, (2) agent asks clarification, (3) user provides specific answer, (4) NOW check for correct tool call.
4. **Annotate expected behavior per scenario:** Each scenario should explicitly state: "Is asking for clarification correct here?" If yes, the evaluator must handle it.

**Detection (warning signs you have this bug):**
- Agent responses that contain questions ("what time?", "how long?") are scored as FAIL
- The "better" variant (by human judgment) scores lower than the "worse" variant
- You read the failure transcripts and think "but that's actually a good response"
- High scores correlate with guessing/assuming rather than precision

**Phase to address:** Phase 1 (scoring design) and Phase 2 (multi-turn infrastructure).

---

### Pitfall 4: Persona-Tool Set Mismatch in Eval Environment

**v1.0 failure:** The eval stripped `recall` and `remember` tools from baseline, but kept the persona that says "First message -> call recall() first. Silently." Haiku obeyed the persona instructions and generated `recall` calls -- but the tool wasn't in the bound schema. Every `recall` call inflated "wrong tool" failure counts. This wasn't hallucination; it was the agent correctly following instructions about tools that weren't available.

**What goes wrong:** The eval creates a "zero persona" or stripped-down environment that differs from production. The system prompt references tools, behaviors, or capabilities that don't exist in the eval context. The LLM reads the system prompt, follows its instructions, and gets penalized for it. The eval is testing "how well does the LLM handle contradictory instructions" rather than "how well does the LLM use these tools."

**Why it happens:** Production system prompts evolve organically. They accumulate references to tools, memory systems, and behaviors. When creating an eval, you copy the system prompt but selectively remove tools. Nobody audits the system prompt for references to removed tools. The LLM, being instruction-following, tries to use what the prompt tells it to use.

**Consequences:**
- v1.0: Baseline generated `recall({})` calls that were counted as "wrong tool" -- inflating failure rates
- Baseline also generated `run_code(remember(...))` as a workaround -- persona said "run_code sandboxed Python with remember(), recall()"
- These weren't model failures -- they were the model correctly following a contradictory eval setup
- Impossible to know how many of the 300+ baseline runs were affected by this persona leak

**Prevention:**
1. **Persona-tool audit:** Before ANY eval run, enumerate every tool mentioned in the persona/system prompt. Verify every mentioned tool is in the eval tool set. If not, either add a mock tool or strip the reference from the persona.
2. **Isolated eval personas:** Create eval-specific personas that ONLY reference the tools available in that eval variant. Don't copy production persona and hope for the best.
3. **Mock unavailable tools:** If the persona references `recall`/`remember` and you don't want to test memory, add dummy tools that accept calls but return a canned response. This prevents the LLM from generating calls to non-existent tools.
4. **Automated persona-tool consistency check:** Write a function that extracts tool names from the persona text (regex for function-call patterns) and asserts every extracted name exists in the tool set.

**Detection (warning signs you have this bug):**
- Agent calls tools that aren't in the bound schema
- Error logs show "unknown tool" or tool call names that don't match any registered tool
- The system prompt mentions capabilities that the eval doesn't provide
- Removing a tool from the eval changes the persona's effectiveness on UNRELATED scenarios

**Phase to address:** Phase 1 (eval environment design) -- before first experiment.

---

### Pitfall 5: Statistical Significance From Evaluator Artifacts

**v1.0 failure:** The p=0.006 result on `hard_ambiguous` was real statistically but partially fabricated by evaluator bugs. The `hard_multi` 100% vs 0% was entirely an evaluator bug. The single-turn bias inflated the gap on `hard_ambiguous`. After accounting for these bugs, the evidence for "routing tax" is substantially weaker than the p-value suggests.

**What goes wrong:** You run a properly designed experiment with proper statistical analysis. The numbers come back significant. You publish the finding. Later, you discover that evaluator bugs created or inflated the signal. The statistics were correct given the data -- but the data was wrong. This is the most dangerous pitfall because the eval LOOKS rigorous. It has confidence intervals, p-values, Fisher exact tests, power analysis -- everything except correct underlying measurements.

**Why it happens:** Statistical rigor is applied to the analysis layer but not the measurement layer. Teams invest in bootstrap CIs, Fisher exact tests, and power analysis while assuming their evaluators are correct. The evaluator is treated as infrastructure that "just works" rather than as a critical measurement instrument that needs its own validation.

**Consequences:**
- v1.0: A REJECT decision was issued based on p=0.006. This looks highly significant.
- The real signal, after accounting for evaluator bugs and single-turn bias, is "substantially weaker than reported"
- If the eval hadn't been audited post-hoc, the wrong decision would have stood
- The v1.0 pipeline looked MORE rigorous than most team evals (660 calls, bootstrap CIs, iterative exploration) -- yet still produced misleading results

**Prevention:**
1. **Validate evaluators BEFORE experiments:** Run golden-response tests for every evaluator x variant combination. The evaluator itself needs tests.
2. **Manual spot-check every significant finding:** When a result is significant, manually read 10+ transcripts from each variant on the significant category. Do the scores match your human judgment?
3. **A/A test:** Run the same variant against itself. If the evaluator shows a significant difference between identical variants, the evaluator is broken.
4. **Evaluator change log:** Track every evaluator modification. If an evaluator changes mid-experiment, ALL data collected with the old evaluator is suspect.
5. **Pre-registration:** Define your evaluator logic, scenarios, and success criteria BEFORE running experiments. This prevents unconscious "fixing" of evaluators to match expected results.

**Detection (warning signs you have this bug):**
- Significant results come from categories where the evaluator logic is most complex
- The significance concentrates in scenarios that exercise variant-specific evaluator paths
- Manual transcript review contradicts automated scores
- The "worse" variant's failures, when read, look like reasonable responses

**Phase to address:** Phase 1 (evaluator validation suite) -- evaluators are tested before they test anything else.

---

### Pitfall 6: Tool Naming Creates Evaluation Confounds

**v1.0 failure:** Users say "remind me" for both one-time and recurring tasks. The applike tool named `reminders_create` captured this word, causing one-time requests to route to the recurring tool. The `reminders_create` tool's only timing parameter was `schedule` (cron expression), which forced recurring behavior even for one-time requests. This was a tool DESIGN problem, not a model CAPABILITY problem, but the eval scored it as model failure.

**What goes wrong:** The eval is supposed to test whether a tool interface design works well. But when the tool design contains a naming trap (a tool name that overlaps with common user language in misleading ways), the eval conflates "the LLM chose the wrong tool" with "the tool naming misled the LLM." You can't tell if the LLM is bad at routing or if the tool names are bad at communicating their purpose.

**Why it happens:** Tool naming is part of the design being tested. You can't isolate "LLM routing ability" from "tool name quality" because the LLM routes BASED on the name. This creates a confound: poor results might mean the LLM is bad at routing, OR they might mean the names are confusing. The eval can't distinguish these causes.

**Prevention:**
1. **Diagnostic annotation:** For each failure, annotate whether the LLM's interpretation of the tool name was reasonable. "User said 'remind me', LLM chose `reminders_create`" is a naming trap, not a routing failure.
2. **Tool name probes:** Test each tool name in isolation: "If the user says X, which tool name SOUNDS like the right match?" If the "correct" tool has a name that sounds WRONG for common requests, the naming is the problem.
3. **Separate routing accuracy from intent accuracy:** Score both: (a) did the LLM pick the right conceptual action? (b) did the LLM pick the right technical tool? If (a) is right but (b) is wrong, the tool naming is the issue.
4. **Evaluate tool designs with naming analysis BEFORE running experiments.**

**Detection:**
- Failures correlate with specific words in user prompts matching the "wrong" tool name
- The LLM's reasoning (when captured) shows it chose the tool BECAUSE of the name match
- Renaming the tool changes the failure pattern

**Phase to address:** Phase 1 (scenario design) and Phase 2 (tool variant design).

---

## Moderate Pitfalls

---

### Pitfall 7: Batch Review Bias -- Post-Hoc Human Review Distorted by Anchoring

**What goes wrong:** After running 660 LLM calls, you sit down to review results in aggregate. You see p=0.006. You're now anchored to "there IS a significant difference." When you review individual transcripts, you unconsciously interpret ambiguous responses in ways that confirm the statistical finding. You find "evidence" for the routing tax because you're looking for it. You miss evaluator bugs because you trust the numbers.

**Why it happens:** Post-hoc review is inherently susceptible to confirmation bias. The reviewer already knows the aggregate result. Human brains pattern-match to confirm existing beliefs. Reviewing 100+ transcripts is cognitively exhausting, making it easy to skim and confirm rather than carefully evaluate each one.

**Prevention:**
1. **Blind review:** Before looking at aggregate statistics, review a random sample of transcripts without knowing which variant produced them and without knowing the eval score. Record your own pass/fail judgment. THEN compare to automated scores.
2. **Adversarial review:** After finding a significant result, specifically look for reasons the result might be WRONG. What evaluator bugs could produce this? What confounds exist?
3. **Pre-register review criteria:** Before reviewing, write down what a "correct" response looks like for each scenario. Then score against your own criteria.
4. **Inter-rater reliability:** If possible, have two people independently review the same transcripts. For solo developers: review once, wait 24 hours, review again.

**Detection:**
- Your human review always agrees with the automated scores
- You can't find any evaluator bugs or confounds after specifically looking for them
- Your review takes less than 1 minute per transcript on complex scenarios

**Phase to address:** Phase 3 (analysis methodology) -- built into the review process.

---

### Pitfall 8: Isolated Experiments Diverge from Production (The Eval-Production Gap)

**What goes wrong:** The eval runs a "zero persona" agent with a stripped tool set in a controlled environment. Production runs a full persona agent with all tools, conversation history, memory, HITL interrupts, and background tasks. The eval agent behaves fundamentally differently because the environment is fundamentally different. Results that hold in eval don't transfer to production.

**Why it happens:** Evals need isolation for controlled comparison. But each thing you strip out (memory, conversation history, other tools, HITL) changes agent behavior. The LLM's tool-use decisions are influenced by the full context -- removing parts changes the decision. It's the evaluation equivalent of testing a fish's walking ability by removing the water.

**Prevention:**
1. **Minimal isolation:** Only strip what you MUST for the experiment. If you're testing tool interface design, keep memory, keep conversation history, keep the full persona. Only change the tools under test.
2. **Integration eval layer:** After isolated experiments, run a small set of integration evals with the full production setup. Verify that isolated findings hold.
3. **Document isolation decisions:** Explicitly list everything stripped from the eval environment and justify each removal. If the justification is weak ("it was easier"), add it back.
4. **Compare eval behavior to production behavior:** For a few common scenarios, run both the eval agent and the production agent. If their behavior diverges substantially on the SAME scenario, your eval environment is too different.

**Detection:**
- Production users report issues that the eval never catches
- The "best" variant in eval performs poorly in production
- Agent behavior changes dramatically when you add/remove non-test-relevant tools
- Eval agent never asks for clarification but production agent frequently does

**Phase to address:** Phase 2 (eval environment design) and Phase 4 (integration validation).

---

### Pitfall 9: Deterministic Evaluators Silently Rot as Tool Interfaces Evolve

**What goes wrong:** You build evaluators that check specific parameter names, tool call structures, and response formats. The tool interface evolves (parameter renamed, new optional field, response structure change). The evaluator keeps running -- no crashes, no errors -- but its checks no longer match the tool interface. It either false-passes (checking a field that no longer exists, defaulting to "OK") or false-fails (checking for an old field name that was renamed).

**Why it happens:** Evaluators are code that tests other code. Like any test, they can go stale. But unlike normal tests (which fail noisily when the interface changes), eval assertions often degrade silently because they check for the PRESENCE of fields (which might just be missing instead of wrong) or check SPECIFIC values (which might have new valid values). Anthropic's engineering blog specifically warns that "checking that agents followed very specific steps like a sequence of tool calls in the right order" produces brittle tests.

**Prevention:**
1. **Schema-driven evaluators:** Generate evaluator checks from the tool schema, not from hardcoded parameter names. If the schema has `schedule`, the evaluator checks `schedule`. If the schema changes to `cron_expression`, the evaluator automatically updates.
2. **Evaluator health checks:** Before each experiment run, execute a small "calibration" set of known-correct responses through the evaluator. If any known-correct response fails, the evaluator has rotted.
3. **Version-pin evaluators to tool versions:** When tool schemas change, require evaluator updates in the same PR. Like API versioning.
4. **Avoid checking tool call ORDER unless order is semantically important.** Check that the right tools were called with the right arguments, not that they were called in a specific sequence.

**Detection:**
- Evaluator hasn't been modified in months but tool interfaces have changed
- New tool variants pass at suspiciously high rates (evaluator not checking new params)
- Old tool variants start failing on scenarios they used to pass (evaluator checking stale param names)
- The evaluator code references parameter names that don't exist in current tool schemas

**Phase to address:** Phase 1 (evaluator architecture) -- design for evolvability from the start.

---

### Pitfall 10: Measuring the Eval Rather Than the System Under Test

**What goes wrong:** Your eval results reflect properties of the eval infrastructure (evaluator bugs, scenario bias, scoring methodology) rather than properties of the system you're testing. You optimize the system to score well on the eval, which is different from optimizing the system to work well for users. Anthropic documents this as a persistent problem: CORE-Bench scores jumped from 42% to 95% after fixing eval bugs, not after improving the model.

**Why it happens:** Any measurement instrument has its own characteristics. When the instrument is complex (multi-step evaluator pipeline with serialization, scoring, aggregation), the instrument's characteristics dominate the signal. Signs include:
- Scores change when you modify the evaluator but not the system
- Different evaluators give different rankings for the same system variants
- Achieving high scores requires understanding the eval's quirks rather than building genuinely better behavior

**Prevention:**
1. **Evaluator invariance test:** Change the evaluator implementation (different but equivalent logic) and verify scores don't change. If they do, the scores depend on evaluator implementation details.
2. **Human-eval correlation:** Regularly compare automated eval scores to human judgment on the same responses. If they diverge, the eval is measuring itself.
3. **A/A test:** Same system, same evaluator, two runs. Results should be statistically identical. If not, the eval has systematic bias or the measurement is too noisy.
4. **Read the transcripts:** As Anthropic emphasizes: "You won't know if your graders are working well unless you read the transcripts and grades from many trials." There is no substitute for looking at the actual data.

**Detection (the definitive signs):**
- Fixing an evaluator bug changes results more than modifying the system under test
- Reading transcripts reveals correct responses scored as failures (or vice versa)
- Scores improve when you "game" the eval format without improving actual behavior
- 100% or 0% scores on any category (too clean -- likely evaluator artifact)
- Different evaluator implementations give different rankings

**Phase to address:** All phases -- this is an ongoing discipline, not a one-time fix.

---

## Minor Pitfalls

---

### Pitfall 11: Likert Scales and Non-Binary Scoring Create Unreliable Signals

**What goes wrong:** You score agent responses on a 1-5 scale. Annotators (human or LLM) default to middle values, the difference between 3 and 4 is subjective and inconsistent, and detecting statistical differences requires much larger sample sizes. Hamel Husain's eval FAQ specifically calls this out: "If your evaluations consist of a bunch of metrics that LLMs score on a 1-5 scale, you're doing it wrong."

**Prevention:** Use binary pass/fail for primary metrics. Force a clear decision. Reserve continuous scores for secondary metrics where gradations genuinely matter (like token cost).

---

### Pitfall 12: Evaluation Cost Escalation

**What goes wrong:** Eval costs balloon to 10x the cost of running the system itself. Each scenario x variant x repetition requires an LLM call. Adding statistical rigor (more reps) multiplies cost linearly.

**Prevention:** Budget upfront. v1.0 spent $2.25 on 660 calls -- affordable. But doubling scenarios, reps, and adding multi-turn would be $18-36. Use caching for regression baselines, only run fresh calls for active experiments. Set a per-experiment budget ceiling.

---

### Pitfall 13: Static Eval Datasets Become Stale

**What goes wrong:** You build a great eval set, run it, get results, make a decision. Six months later, the agent has evolved, user patterns have changed, and the eval set no longer represents real usage. You re-run the old eval and get high scores, falsely concluding everything is fine.

**Prevention:** Version eval datasets. Tag them with the date, system version, and user behavior assumptions. Periodically mine real conversations for new scenarios. Treat eval datasets as living documents, not artifacts.

---

### Pitfall 14: Assuming Negative Results Mean "Doesn't Exist"

**What goes wrong:** You test for a behavior, don't find it, and conclude the system can't do it. But the eval environment was wrong (persona mismatch), or the evaluator didn't check for it (parameter coverage gap), or the scenario didn't elicit it (single-turn limitation). Absence of evidence is not evidence of absence.

**Prevention:** When a result is negative, ask: "Could the eval have missed this?" Check evaluator coverage, persona-tool consistency, and scenario design before concluding the system lacks a capability.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | v1.0 Precedent |
|-------------|---------------|------------|-----------------|
| Response serialization | Pitfall 1: Type coercion data loss | Defensive union-type handling, completeness assertions | `content` list serialized as `""` |
| Evaluator design | Pitfall 2: Incomplete parameter coverage | Golden-response tests per variant, exhaustive param whitelist | `_check_has_timing` missed `schedule` |
| Scoring methodology | Pitfall 3: Single-turn penalizes clarification | Ambiguous-scenario classification, multi-turn support | "guessing > clarification" reward |
| Eval environment | Pitfall 4: Persona-tool mismatch | Automated persona-tool audit, eval-specific personas | Persona said "call recall()" but tool wasn't available |
| Statistical analysis | Pitfall 5: Significance from evaluator artifacts | Evaluator validation BEFORE experiments, manual spot-checks | p=0.006 partially from evaluator bugs |
| Tool variant design | Pitfall 6: Naming confounds | Diagnostic annotation separating routing from naming | "remind me" -> `reminders_create` naming trap |
| Post-hoc analysis | Pitfall 7: Anchoring bias in batch review | Blind review protocol, adversarial review | Significant result accepted without questioning evaluator |
| Production integration | Pitfall 8: Eval-production gap | Minimal isolation, integration eval layer | Zero-persona agent behaved differently than production |
| Evaluator maintenance | Pitfall 9: Evaluator rot | Schema-driven checks, evaluator health checks | Dead `do_later` branches, stale param assumptions |
| Overall validity | Pitfall 10: Measuring eval not system | A/A tests, human-eval correlation, transcript reading | CORE-Bench: 42% -> 95% from eval fixes alone |

---

## The v1.0 Failure Taxonomy

Mapping v1.0's 5 systemic bugs to pitfall categories:

| v1.0 Bug | Pitfall Category | Severity | Would v2 Catch It? |
|----------|-----------------|----------|---------------------|
| Response text discarded (list -> "") | Data loss (Pitfall 1) | Critical | Yes, if serialization smoke test added |
| `_check_has_timing` missed `schedule` | Evaluator coverage (Pitfall 2) | Critical | Yes, if golden-response tests per variant |
| Single-turn rewards guessing | Scoring methodology (Pitfall 3) | Critical | Yes, if ambiguous scenarios classified separately |
| Persona references unavailable tools | Environment mismatch (Pitfall 4) | Moderate | Yes, if persona-tool audit automated |
| "reminder" -> `reminders_create` naming trap | Design confound (Pitfall 6) | Moderate | Partially -- requires diagnostic annotation discipline |

**Key insight:** ALL five v1.0 bugs would have been caught by standard eval validation practices (golden tests, smoke tests, persona audits). None required sophisticated tooling. They were process failures, not technology failures.

---

## Recovery Strategies

If pitfalls occur despite prevention:

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Response data loss (P1) | LOW | Fix serialization, re-run affected experiments, compare results |
| Evaluator coverage gap (P2) | MEDIUM | Fix evaluator, re-run experiments on affected variants, recompute statistics |
| Single-turn scoring bias (P3) | HIGH | Redesign scoring for ambiguous scenarios, potentially re-run entire experiment |
| Persona-tool mismatch (P4) | MEDIUM | Fix persona, re-run baseline experiments, compare to original results |
| Significance from artifacts (P5) | HIGH | Full re-analysis required; may invalidate published decisions |
| Naming confounds (P6) | MEDIUM | Add diagnostic annotations, re-analyze existing data |
| Anchoring bias in review (P7) | MEDIUM | Blind re-review of transcripts; may change conclusions |
| Eval-production gap (P8) | HIGH | Integration eval suite needed; isolated results may not transfer |
| Evaluator rot (P9) | LOW | Schema-sync evaluators, run calibration set, fix mismatches |
| Measuring eval not system (P10) | HIGH | A/A test + human correlation check; may require eval redesign |

---

## The Meta-Pitfall: Thinking You've Fixed It

The most dangerous state is "we learned from v1.0, so v2.0 will be fine." v1.0 LOOKED rigorous: 660 LLM calls, bootstrap CIs, iterative exploration, Fisher exact tests, power analysis, lab notebook methodology. It had more statistical sophistication than most team evals. It still produced misleading results.

**The fix is not more sophistication. The fix is more verification.** Test the evaluators. Read the transcripts. Run A/A tests. Do blind reviews. Check the data at every stage. The sophistication of the analysis is worthless if the measurement is wrong.

---

## Sources

### Primary (HIGH confidence -- from v1.0 codebase and post-mortem)
- `/Users/iorlas/Projects/my/serega/docs/eval-failure-analysis.md` -- v1.0 post-mortem with all 5 bugs documented
- `/Users/iorlas/Projects/my/serega/tests/eval/evaluators.py` -- v1.0 evaluator code showing exact bugs
- `/Users/iorlas/Projects/my/serega/.planning/milestones/v1.0-phases/05-full-comparison/EXPLORATION.md` -- full experiment data (660 calls)
- `/Users/iorlas/Projects/my/serega/scripts/eval_probe.py` -- v1.0 diagnostic script showing response serialization fix

### Secondary (MEDIUM confidence -- verified industry sources)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- task design failures, grader bugs, transcript reading as validation
- [Hamel Husain: LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) -- binary scoring, error analysis first, 60-80% time on understanding failures
- [Block Engineering: Testing Pyramid for AI Agents](https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents) -- brittle assertions, tool interface evolution, measurement-based validation
- [Monte Carlo: AI Agent Evaluation - 5 Lessons](https://www.montecarlodata.com/blog-ai-agent-evaluation/) -- evaluators hallucinating, cost escalation, non-determinism
- [HoneyHive: Avoiding Common Pitfalls in LLM Evaluation](https://www.honeyhive.ai/post/avoiding-common-pitfalls-in-llm-evaluation) -- static datasets, statistical rigor timing

### Tertiary (LOW confidence -- general patterns, needs validation for this specific context)
- [Confident AI: Single vs Multi-Turn Evals](https://www.confident-ai.com/docs/llm-evaluation/core-concepts/single-vs-multi-turn-evals) -- multi-turn reveals problems single-turn misses
- [Pragmatic Engineer: LLM Evals for Devs](https://newsletter.pragmaticengineer.com/p/evals) -- evaluation biases
- [Pillar Security: Multi-Turn Tests vs Single-Turn](https://www.pillar.security/blog/practical-ai-red-teaming-the-power-of-multi-turn-tests-vs-single-turn-evaluations) -- attack success rates increase 27% in multi-turn

---
*Pitfalls research for: Eval Pipeline Rebuild (post-v1.0 failure analysis)*
*Researched: 2026-02-20*
