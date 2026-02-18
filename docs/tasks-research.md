# Tasks & Tool Design Research

Living doc. Updated as evals produce results.

## Design Principles

Based on Anthropic, BFCL, MCPVerse, Letta research:

1. **Tools describe HOW. Persona describes WHEN.** (Anthropic + OpenAI guidance)
2. **Fewer params > more params.** 1-5 safe. 6+ degrades accuracy. (BFCL)
3. **No overlapping intent expressions.** delay_seconds vs when = confusion. (Anthropic)
4. **Consolidate chained workflows.** If always called together, merge. (Anthropic)
5. **Self-documenting tools with examples.** 72% → 90% accuracy. (Anthropic)
6. **Evaluate before committing.** Measure, don't guess.

## Hard Data

### Tool Count vs Accuracy (MCPVerse)
- Claude-4-Sonnet **uniquely scales** with more tools (+3.2 pts at 218 tools)
- GPT-4o: **-24.5 pts** at 218 tools. Most models degrade.
- With 10 tools we're fine on count. Issue is param complexity + token overhead.

### Parameter Complexity (BFCL)
- 1-5 params: easy. 6-10: increased errors. 10+: high risk.
- Our `update_task` has 6 params. `schedule_task` has 5. Both borderline.

### Tool Descriptions (Anthropic)
- Claude-optimized tool descriptions: 60% → **80% accuracy**
- Tool examples: 72% → **90% accuracy** on complex params

### Think Tool (Anthropic)
- Tau-bench airline: baseline 0.370 → think tool **0.570** (+54%)
- **Current recommendation: use extended thinking instead in most cases**
- Think tool still better for: long tool chains, policy-heavy, costly mistakes

### Token Budget (Current)
| Component | Tokens/request |
|-----------|---------------|
| Task tool schemas (3 tools, 12 params) | ~575 |
| Persona task section (34 lines) | ~479 |
| **Task overhead total** | **~1,054** |
| Think tool schema | ~40 |
| All 10 tools total | ~1,800 (est) |
| Full persona (110 lines) | ~1,200 (est) |

## Heartbeat

### What It Is
- **OpenClaw**: HEARTBEAT.md = standing checklist. Agent reads every 30min, processes, responds.
  **It IS an LLM invocation every cycle.** Cost: skip-if-empty, cheaper model, active hours.
- **Letta/MemGPT**: `request_heartbeat` = tool param for multi-step chaining.
  **DEPRECATED in V1.** Modern models chain natively. *"Stay in-distribution."*
- **Our system**: Already supports via `schedule_task(recurring=True)` + cron. Zero code changes.

### Why People Love It
- "First time AI felt less like a chatbot and more like an always-on employee"
- Agent completed research overnight, user woke to results
- Checks Slack, creates PRs, monitors Sentry, generates content
- **The value is proactive behavior, not the mechanism.**

### Why People Hate It
- Default heartbeats on Opus: **~$5/day ($150/month) to do nothing**
- One user checking email every 5min: **$50 burned in one day**
- Federico Viticci: **$3,600/month** from 1.8M tokens
- Agent sent 500 iMessages to wife, required pulling power cord
- "Users found themselves supervising agents more than delegating"

### Proactivity Research (Academic)
| Study | Finding |
|-------|---------|
| CHI 2024 (N=24) | Users prefer **medium proactivity** — suggest, don't act |
| Springer BISE (N=92) | Proactive help **reduces satisfaction** (threatens self-esteem) |
| Dev field study (N=15) | 52% engagement, only **27% rated reliable** |
| CHI 2025 (N=18) | Increases efficiency but **disrupts workflow** |

## Eval Variants

### Tool Surface (tested in `test_task_scheduling_eval.py`)

| Variant | Tool | Params | Hypothesis |
|---------|------|--------|-----------|
| `baseline` | schedule_task | 5 (title, desc, when, delay_seconds, recurring) | Control |
| `desc_only` | schedule_task | 5 | Better desc → better behavior |
| `minimal_when` | schedule_task | 3 (title, desc, when) | Fewer params, less confusion |
| `do_later` | do_later | 2 (what, when) | Natural language minimal |
| `self_doc_only` | schedule_task | 5 | Rich tool desc, zero persona → is persona needed? |
| `consolidated` | tasks | 8 (action, title, desc, ...) | One tool for all task ops |

### Persona (orthogonal axis)

| Variant | Task section |
|---------|-------------|
| `full_persona` | Current 34 lines |
| `compressed` | ~8 lines (WHEN only) |
| `zero_persona` | No task section |

## Results

### Round 1 (2026-02-17) — 60/63 passed (95.2%)

Model: `claude-haiku-4-5-20251001` via OpenRouter. Temperature 0. Single-turn (no tool results fed back).

**Tool Variants** (all use `PERSONA_FULL` except `self_doc_only` which uses `PERSONA_ZERO_TASKS`):

| Variant | Params | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|--------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| baseline | 5 | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | 6/7 |
| desc_only | 5 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | 6/7 |
| minimal_when | 3 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| do_later | 2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| self_doc_only | 5 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| consolidated | 8 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |

**Persona Variants** (all use `DESC_FIXED` / desc_only tool):

| Variant | Task section | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|-------------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| full_persona | 34 lines | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | 6/7 |
| compressed | 8 lines | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| zero_persona | 0 lines | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |

**Failure Analysis:**

1. **baseline × seq:10**: Scheduled 1 task instead of 10. DESC_BASELINE lacks sequence instruction → model delegates counting to a single task.
2. **desc_only × self:morning** and **full_persona × self:morning**: 0 tool calls. Same root cause: `DESC_FIXED + PERSONA_FULL` combo. The sequence-heavy description ("For sequences, call once per task with staggered delay_seconds") likely primes the model toward sequences, making it uncertain for simple recurring tasks. Model chose to respond conversationally instead.

**Key Findings:**

- **Fewer params validated**: `minimal_when` (3) and `do_later` (2) both 7/7. Matches BFCL research.
- **Persona task section adds noise**: `compressed` and `zero_persona` both outperform `full_persona` (7/7 vs 6/7). Full 34-line task section may be counterproductive.
- **Self-documenting tools work**: `self_doc_only` (zero persona + rich tool desc) = 7/7. Tool docs > persona for HOW.
- **Consolidation doesn't hurt (yet)**: `consolidated` (8 params) still 7/7. Action dispatch works for Haiku.
- **desc_only's sequence example is too dominant**: Hurts the generic "check on me every morning" case.

### Round 2 (2026-02-17) — 49/49 passed (100%)

Cross-product combos of Round 1 winners + targeted fixes.

**Combo Variants:**

| Variant | Tool | Params | Persona | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|------|--------|---------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| minimal_when__compressed | schedule_task | 3 | compressed | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| minimal_when__zero | schedule_task | 3 | zero | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| do_later__zero | do_later | 2 | zero | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| do_later__compressed | do_later | 2 | compressed | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| do_later_terse__zero | do_later | 2 | zero | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| desc_fixed_v2__full | schedule_task | 5 | full | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |
| self_doc__compressed | schedule_task | 5 | compressed | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **7/7** |

**Key findings:**

- **All 7 combos = 7/7**. No failures. Every hypothesis confirmed.
- **desc_fixed_v2 fixes the recurring failure**: Adding an explicit recurring example to DESC_FIXED (`'check on me every morning' → schedule_task(..., when='0 8 * * *', recurring=True)`) resolves the self:morning failure even with full persona. Examples are king.
- **Ultra-terse works**: `do_later_terse__zero` (2-line description, zero persona) = 7/7. Haiku needs very little guidance.
- **Minimum viable config**: `do_later__zero` or `do_later_terse__zero` — 2 params, zero persona task section, 100% pass rate.

### Round 3 (2026-02-17) — Corrected Methodology, 548/560 passed (97.9%)

**Methodology change**: Rounds 1+2 used `ChatOpenAI` via OpenRouter with `temperature=0`. This didn't match production, which uses `ChatAnthropic` (direct Anthropic API) with no temperature set (Anthropic default = 1.0). Round 3 corrects this:

| Aspect | Rounds 1+2 (wrong) | Round 3 (matches production) |
|--------|---------------------|------------------------------|
| Client | `ChatOpenAI` via OpenRouter | `ChatAnthropic` (direct) |
| Temperature | 0 (deterministic) | None → Anthropic default (1.0) |
| API | OpenRouter proxy | Direct Anthropic API |
| Tool format | OpenAI-compatible (translated) | Anthropic native |
| Repetitions | 1x per test | 5x per test |

**Tool Variants** (5 runs each, N/5 = pass count):

| Variant | Params | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|--------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| baseline | 5 | 3/5 | **0/5** | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **28/35** |
| desc_only | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| minimal_when | 3 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| do_later | 2 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| self_doc_only | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| consolidated | 8 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | **34/35** |

**Persona Variants** (all use `DESC_FIXED` / desc_only tool):

| Variant | Task section | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|-------------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| full_persona | 34 lines | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| compressed | 8 lines | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| zero_persona | 0 lines | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |

**Combo Variants:**

| Variant | Tool | Params | Persona | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|------|--------|---------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| minimal_when__compressed | schedule_task | 3 | compressed | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| minimal_when__zero | schedule_task | 3 | zero | 5/5 | 5/5 | 3/5 | 5/5 | 5/5 | 5/5 | 5/5 | **33/35** |
| do_later__zero | do_later | 2 | zero | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| do_later__compressed | do_later | 2 | compressed | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| do_later_terse__zero | do_later | 2 | zero | 5/5 | 4/5 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 | **33/35** |
| desc_fixed_v2__full | schedule_task | 5 | full | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |
| self_doc__compressed | schedule_task | 5 | compressed | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |

**Failure Analysis:**

1. **baseline × seq:3 (3/5)** and **baseline × seq:10 (0/5)**: DESC_BASELINE lacks sequence instruction. At temp=1.0, the model consistently delegates counting to a single task instead of N separate calls. This was 6/7 at temp=0 — the "PASS" was the lucky deterministic path.
2. **consolidated × self:morning (4/5)**: 1 run produced 0 tool calls. The `tasks` consolidated tool's 8-param action-dispatch sometimes confuses the model at high temperature.
3. **minimal_when__zero × seq:msg (3/5)**: Without persona, `schedule_task(3 params)` occasionally doesn't split "3 messages 1 min apart" into 3 calls.
4. **do_later_terse__zero × seq:10 (4/5)**: Ultra-terse description + zero persona + high N sequence — fell back to `run_code` once.
5. **do_later_terse__zero × seq:msg (4/5)**: Only scheduled 2/3 messages in one run.

**Key Findings (Round 3 vs Rounds 1+2):**

- **temp=0 was NOT significantly inflating results**: 97.9% at temp=1.0 vs 97.3% at temp=0. The overall pass rate is comparable. Temp=0 was hiding `baseline`'s seq weakness but also hid that `desc_only × self:morning` actually works at temp=1.0 (5/5 vs 6/7 in R1).
- **baseline is worse than thought**: 0/5 on seq:10 (was 6/7 at temp=0). Without explicit sequence instructions, the model reliably collapses sequences into a single task.
- **desc_only is better than thought**: Fixed self:morning failure from R1 — now 35/35. The R1 failure was the unlucky deterministic path at temp=0.
- **Top performers (35/35 across 5 runs)**: `desc_only`, `minimal_when`, `do_later`, `self_doc_only`, all persona variants, `minimal_when__compressed`, `do_later__zero`, `do_later__compressed`, `desc_fixed_v2__full`, `self_doc__compressed`.
- **Ultra-terse too fragile**: `do_later_terse__zero` dropped from 7/7 (temp=0) to 33/35 (temp=1.0). Minimal guidance + high temperature = occasional failures.
- **Native Anthropic API works as well as OpenRouter**: No regressions from switching API pathway — tool use works identically.

### Combined Analysis (Rounds 1-3)

**672 total test invocations. 657 passed (97.8%).**

Round 3 (corrected methodology) validates Round 1+2 conclusions with minor refinements:

#### Updated Conclusions

1. **Fewer params = better** (confirmed): 2-3 params consistently 35/35 at temp=1.0. 5 params works if description is good. 8 params (consolidated) has a small reliability gap (34/35).

2. **Persona task section is unnecessary for HOW** (confirmed): All 3 persona variants scored 35/35. Full persona no longer fails (was 6/7 in R1, now 35/35 — the R1 failure was temp=0 bad luck).

3. **Examples beat parameter design** (confirmed): `desc_only` (with explicit sequence example) now 35/35 even with full persona. `baseline` (no sequence example) is 28/35.

4. **Natural language params work as well as structured** (confirmed): `do_later(what, when)` = 35/35 across all combos with non-zero persona.

5. **Don't go ultra-terse** (new): `do_later_terse__zero` dropped to 33/35. There's a minimum viable description threshold below which temp=1.0 causes failures. 2-line desc + zero persona is too lean.

6. **Zero persona + minimal tool = fragile combo** (new): `minimal_when__zero` also 33/35. Zero persona removes behavioral context that helps with ambiguous prompts like "send me 3 messages."

#### Recommended Production Changes (updated)

| Change | Rationale | Confidence |
|--------|-----------|------------|
| Adopt `minimal_when` signature (3 params) | 35/35 with compressed persona at temp=1.0. Best reliability/simplicity trade-off. | High |
| Add recurring example to tool description | Prevents sporadic recurring failures. desc_only now 35/35. | High |
| Compress persona task section to ~8 lines | All persona variants 35/35. Save 400+ tokens. Avoid zero (too lean). | High |
| Consider `do_later` rename | 35/35 with compressed persona. More natural. | Medium |
| Keep separate tools (don't consolidate) | `consolidated` 34/35 vs 35/35 for simpler tools. | High |
| Don't use ultra-terse descriptions | `do_later_terse__zero` = 33/35. Minimum viable description needed. | High |

### Round 4 (2026-02-17) — `typed_when` variant, 68/70 passed (97.1%)

**Goal**: Validate a stricter `when` parameter that accepts **typed values**: `int` for seconds, ISO string for absolute time, cron string for recurring. Avoids NLP parsing entirely — backend just detects the format. Signature: `when: int | str = ""`.

**Variants tested** (5 runs each):

| Variant | Tool | Params | Persona | seq:3 | seq:10 | seq:msg | single | multi | self:morning | self:11pm | **Score** |
|---------|------|--------|---------|-------|--------|---------|--------|-------|-------------|-----------|-----------|
| typed_when | schedule_task | 3 (int\|str) | full | 5/5 | **4/5** | 5/5 | 5/5 | 5/5 | **4/5** | 5/5 | **33/35** |
| typed_when__compressed | schedule_task | 3 (int\|str) | compressed | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **35/35** |

**Failure Analysis:**

1. **typed_when × seq:10 (4/5)**: Model collapsed 10-count sequence into a single task with `when=5`. Same failure pattern as baseline — at temp=1.0, without compressed persona, high-N sequences occasionally get delegated.
2. **typed_when × self:morning (4/5)**: 0 tool calls in 1 run. Model responded conversationally instead of scheduling. Same pattern as other full-persona variants in earlier rounds.

**Key Questions Answered:**

1. **Does the LLM output `when=300` (int) or `when="300"` (string)?** → Consistently uses **int** for delays (e.g., `when=5`, `when=10`). The union type works correctly.
2. **Does it use ISO for absolute and cron for recurring?** → Yes. ISO strings for specific times, cron for recurring. No format confusion observed.
3. **Does stagger logic work with int when?** → Yes. `when=5, when=10, when=15` pattern works correctly (strictly increasing ints).
4. **Does compressed persona + typed_when match full persona?** → **Compressed beats full**: 35/35 vs 33/35. Consistent with all prior rounds.

**Comparison with `minimal_when` (string-only `when: str`):**

| Variant | Persona | Score | Notes |
|---------|---------|-------|-------|
| minimal_when | full | 35/35 | R3 benchmark |
| minimal_when__compressed | compressed | 35/35 | R3 benchmark |
| typed_when | full | 33/35 | -2 vs minimal_when |
| typed_when__compressed | compressed | **35/35** | Matches minimal_when |

**Conclusion**: `typed_when` with compressed persona matches `minimal_when` perfectly (35/35). Full persona introduces the same sporadic failures seen in other variants. The typed approach is viable for production — backend gets cleaner input (int vs string parsing) with no accuracy cost when paired with compressed persona.

## Deferred (Pending Eval Results)

- Production tool changes (`tasks/tools.py`)
- Persona changes (`persona.md`)
- Heartbeat as infrastructure (already works via recurring tasks)
- Think tool evaluation
- Dynamic tool loading
- Two-assistant split

## Sources

- Anthropic tool guide: https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic think tool: https://www.anthropic.com/engineering/claude-think-tool
- Anthropic advanced tools: https://www.anthropic.com/engineering/advanced-tool-use
- MCPVerse (tool count): https://arxiv.org/html/2508.16260v1
- BFCL leaderboard: https://gorilla.cs.berkeley.edu/leaderboard.html
- Letta V1 blog: https://www.letta.com/blog/letta-v1-agent
- OpenClaw docs: https://docs.openclaw.ai/gateway/heartbeat
- OpenClaw cost analysis: https://www.notebookcheck.net/Free-to-use-AI-tool-can-burn-through-hundreds-of-Dollars-per-day-OpenClaw-has-absurdly-high-token-use.1219925.0.html
