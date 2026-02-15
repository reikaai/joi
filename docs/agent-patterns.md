# Context Management Cost Framework

Decision framework for evaluating trim vs summarize strategies, accounting for prompt caching economics, context quality degradation, and window limits across providers.

---

## Prompt Caching Fundamentals

LLM providers cache the KV-cache of prompt prefixes. Key properties:

- **Prefix-based**: only the longest matching prefix from the start of the prompt is cached
- **Append-only friendly**: adding messages at the end preserves the cache; inserting/deleting/reordering breaks it
- **What breaks caching**: system message mutation, message deletion or reordering, timestamps injected into prompts, summarization that replaces message history
- **Opt-in vs auto**: Anthropic (including via OpenRouter) requires explicit `cache_control` breakpoints on content blocks. OpenAI and Google auto-cache without any annotation.
- **TTL**: Anthropic offers 5-min (default, refreshes on each hit) and 1-hour (for gaps >5min between requests). Active conversations keep cache alive via refresh.
- **Write/read asymmetry**: cache writes cost 1.25x base (5-min TTL) or 2x (1-hour TTL). Cache reads cost 0.1x base. A single-turn request with no subsequent hits is a net 25% cost increase. Multi-turn conversations see massive savings after the first hit.
- **Summarization interaction**: summarization breaks the conversation prefix cache (rewrites system message + message list). Independent `cache_control` breakpoints on tools survive summarization since tools are first in the prefix order (tools → system → messages).

### Provider Pricing (as of 2025)

| Provider | Input $/MTok | Cached Read $/MTok | Cache Write $/MTok | Discount (D) |
|----------|-------------|-------------------|-------------------|--------------|
| Claude Sonnet 4 | $3.00 | $0.30 | $3.75 | 10x |
| Claude Haiku 4.5 | $0.80 | $0.08 | $1.00 | 10x |
| GPT-4o | $2.50 | $1.25 | auto | 2x |
| Gemini 2.0 Flash | $0.10 | $0.025 | auto | 4x |

D = c_uncached / c_cached_read — the cache discount ratio. Higher D means caching saves more per token. "auto" = provider handles cache writes transparently (no extra write cost exposed).

---

## Per-Turn Break-Even: Trim vs Summarize

The question: when is reading cached full history cheaper than reading an uncached summary?

Let:
- H = history size (tokens)
- R = compression ratio (H / summary_size), typically 3-5x
- K = summary generation overhead (tokens for the summarization call)
- c_cached = cost per cached input token
- c_uncached = cost per uncached input token

**Cached full history cost per turn:**
```
C_cache = H × c_cached
```

**Summarized cost per turn** (summary is uncached because it changes each time):
```
C_summary = (H/R + K) × c_uncached
```

Summarization wins when C_summary < C_cache:
```
(H/R + K) × c_uncached < H × c_cached
```

Ignoring K (best case for summarization), the minimum compression ratio for summarization to break even:
```
R > c_uncached / c_cached = D
```

### Per-Turn Verdict

| Provider | Discount D | Min R needed | Typical R (3-5x) | Verdict |
|----------|-----------|-------------|-------------------|---------|
| Claude | 10x | >10x | No | Caching always wins per-turn |
| GPT-4o | 2x | >2x | Yes | Summarization can win |
| Gemini Flash | 4x | >4x | Borderline | Only with aggressive compression |

For Claude: summarization **cannot** beat caching on a per-turn basis with realistic compression ratios. The 10x discount is too large.

### Absolute Cost Analysis

The ratio analysis above is correct but misleading in isolation. Look at the actual dollar amounts:

```
At 200K tokens (Claude max window):
- Cached full history:  200K × $0.30/MTok = $0.06/turn
- Summarized (4x):      50K × $3.00/MTok = $0.15/turn
- Difference: $0.09/turn

The ratio says "never summarize" (R < D). But $0.09/turn is small.
When quality degradation is the binding constraint, paying $0.09 more
per turn for a 4x shorter context is a reasonable tradeoff.
```

At smaller context sizes the difference shrinks further. At 100K: $0.03 vs $0.075 — a $0.045/turn gap. Cost ratios matter for high-volume production workloads; for agent conversations, the absolute difference is often negligible compared to the quality impact of context length.

---

## Lifecycle Cost Analysis

Per-turn analysis misses the growth dynamics. As conversation grows, the cached prefix grows too.

### Without resets (append-only)

Each turn reads the full (growing) history. Total cost over T turns:
```
C_total = c_cached × Σ(t=1..T) H_t ≈ c_cached × T × H_avg
```

Since H grows roughly linearly: H_avg ≈ T×δ/2 where δ = avg tokens per turn.

**Total cost is O(T²)** — quadratic in conversation length.

### With periodic resets (trim/summarize every N turns)

Reset at intervals of N turns. Within each window, cost is O(N²). Over T/N windows:
```
C_total ≈ (T/N) × c_uncached × N² × δ/2 = T × N × δ/2 × c_uncached
```

**Total cost is O(T×N)** — linear in conversation length for fixed window size.

### When does lifecycle cost matter?

For Claude (10x discount, 200k context window):
- Per-turn cost at window limit: 200k × $0.30/MTok = **$0.06**
- You hit the context window limit before cost becomes a concern
- Reset strategy is driven by **context window limits**, not cost

For GPT-4o (2x discount, 128k window):
- Per-turn cost at window limit: 128k × $1.25/MTok = **$0.16**
- Summarize early; lifecycle savings kick in fast with only 2x discount
- Reset strategy is driven by **cost**, not just window limits

---

## Context Quality Degradation

Cost analysis treats context as a resource management problem. But context length also degrades reasoning quality — independent of retrieval or information placement.

### The problem

Accuracy drops with context length even when all relevant information is present and retrievable. This is not about "lost in the middle" needle-finding — it's about the model's ability to reason over the full context degrading as that context grows.

### Key findings

| Finding | Drop | Source |
|---------|------|--------|
| Info placed mid-context | >30% | Liu et al. (TACL 2024) |
| Even with perfect retrieval | 14-85% | Du & Tian (EMNLP 2025) |
| GPT-4.1: 8K→1M tokens | 84%→50% | Zep/OpenAI (2025) |
| 300 tok vs 113K tok prompt | 30% | Chroma Context Rot (2025) |
| Models holding quality at claimed 32K | 4/17 | NVIDIA RULER (2024) |

### Provider-specific degradation

| Provider | Degradation Profile |
|----------|-------------------|
| Claude | <5% across 200K (slowest decay, best-in-class) |
| GPT-4o/4.1 | Moderate — drops accelerate past 64K |
| Gemini 2.5 | Starts to mess up earlier with wild variations |

### Implication

Quality creates a **soft ceiling** below the hard window limit. Even when caching makes long context cheap, quality makes it unwise. This means the reset decision cannot be purely economic — a shorter context at slightly higher cost may produce significantly better reasoning.

---

## Reset Strategies

Two orthogonal concerns: slowing context growth (observation masking) and compressing when growth exceeds a threshold (trim/summarize).

### Observation masking (always apply)

Replace old tool outputs with `[Output truncated]` while keeping message structure intact.

- Slows context growth, extends runway before any constraint triggers
- **Partially preserves cache**: prefix up to the first masked observation stays cached; content after the masked point is reprocessed. Unlike trim and summarize, which break cache entirely, masking retains the cached prefix for everything before the edit
- Orthogonal to the trim/summarize decision — it just delays when you need to make that choice
- No extra LLM call, no latency cost

### Compression strategies (triggered at H_compress)

| Strategy | Cache Break | Info Loss | Extra LLM Call | When to Use |
|----------|-----------|-----------|----------------|-------------|
| Summarize + trim | Yes | Partial (summary retains key info) | Yes | Default — summarize at H_compress, trim at H_window as safety net |
| Trim only | Yes | Full | No | Latency-critical, or external memory (mem0) handles retention |

**Summarize subsumes trim.** Trim alone is a degenerate case — justified only when:
- Summarization latency is unacceptable
- External memory (mem0) handles followup quality
- Provider has gentle quality degradation AND high cache discount (Claude)

When H_compress is small (low D, steep quality degradation) → summarization is critical — you hit the threshold quickly and need to compress aggressively.

When H_compress is large (high D, gentle degradation) → summarization matters less, especially with mem0 as a memory layer. Yet with prompt caching, the cost penalty for summarization is small in absolute terms (~$0.09/turn at 200K for Claude), so it's rarely worth avoiding.

---

## Scratchpad Think Tool

A no-op tool that gives the model structured space to reason mid-response. The model writes its reasoning as the tool input; the tool returns "OK". No output pollution — thinking stays in tool_use blocks, not assistant content.

**Why it works**: tool_use forces the model to pause, structure its reasoning, and commit to it before continuing. Unlike chain-of-thought in assistant content, it doesn't leak reasoning to the user and doesn't pollute the response.

**Cost**: near-zero. Only output tokens for the tool_call content (~50-200 tokens). No input token overhead. The tool itself does nothing.

**Benchmark results** ([Anthropic blog](https://www.anthropic.com/engineering/claude-think-tool)):
- tau-bench airline: +54% (0.370 → 0.584 with optimized prompt)
- tau-bench retail: +3.7% (0.783 → 0.812)
- SWE-bench: +1.6% (p < .001)

**vs extended thinking**: Extended thinking has a budget minimum of 1024 tokens/turn billed as output tokens ($5/MTok on Haiku 4.5) — ~$0.005/turn even when not needed. Scratchpad costs nothing when not used, and the model self-selects when to invoke it.

**vs model escalation**: Escalation has the meta-reasoning problem (Haiku can't reliably judge when it needs Sonnet) and context tax (every escalation pays Sonnet input rates on the full context). Scratchpad is additive — can layer escalation on top later.

**Implementation**: `src/joi_agent_langgraph2/graph.py` — `think()` tool + persona guidance in `src/joi_agent/persona.md`.

Key insight: just adding the tool helps, but pairing with explicit prompt guidance for when to think yields dramatically better results.

---

## Web Browsing Strategy

### Tiered approach

**Tier 1 (current): Anthropic native tools** — `web_search` + `web_fetch`. Server-side, zero infrastructure, zero bot detection risk. Covers ~80% of web use cases: looking up facts, reading articles, research, fetching URLs shared by the user.

**Tier 2 (deferred): Playwright MCP browser delegate** — for JS-rendered content, form filling, clicking through SPAs. Same delegate pattern as media agent, filtered to ~7 essential tools. Not implementing until a concrete use case demands it.

### Why native first

| Concern | Native (web_search + web_fetch) | Playwright MCP |
|---------|--------------------------------|----------------|
| Coverage | "look up X", read articles, research | JS-rendered, forms, interaction |
| Code change | ~5 lines (dict tools) | ~100+ lines (new delegate, MCP, config) |
| Infrastructure | None (Anthropic server-side) | Docker container |
| Bot detection | Zero risk | Needs stealth measures |
| Cost | search $10/1K, fetch FREE | Token costs + compute |
| Tool count | 0 new tools for agent routing | 26+ (needs filtering to ~7) |

### Cost

- `web_search`: $10/1K searches. At ~20 searches/day ≈ $6/month
- `web_fetch`: FREE (only input token costs). Average page ~2,500 tokens ≈ $0.002/fetch
- `max_uses` bounds per-request: 5 searches, 3 fetches

### Limitations (when Tier 2 is needed)

- JS-rendered SPAs (React/Vue apps that need hydration)
- Sites behind login / CAPTCHA
- Multi-step form interactions
- Content that requires scrolling or clicking to reveal

### Implementation

`web_search` and `web_fetch` are dict-based built-in tools passed to `create_agent()`. `langchain-anthropic` detects them via `_is_builtin_tool()`, auto-injects the required beta header (`web-fetch-2025-09-10`), and routes server-side responses (`server_tool_use`, `web_search_tool_result`, `web_fetch_tool_result`) without client-side `ToolNode` execution.

References: [web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool), [web fetch](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool)

---

## Decision Framework

```
Observation masking: always apply (slows growth, extends runway).

Three constraints determine when to compress (the actual trim/summarize decision):

1. H_cost — cost-driven threshold
   If R < D: H_cost = ∞ (caching always cheaper per turn)
   If R > D: H_cost = K × c_uncached / (c_cached - c_uncached/R)
   But check absolute cost — if |C_cached - C_summary| < $0.10/turn,
   cost is not the deciding factor.

2. H_quality — quality-driven threshold
   Provider-specific, for complex reasoning tasks:
   Claude: ~150-200K (gentle slope, <5% degradation)
   GPT-4o: ~50-80K (accelerates past 64K)
   Gemini: ~30-50K (variable, early onset)

3. H_window — hard context window limit
   Claude: 200K, GPT-4o: 128K, Gemini 2.0 Flash: 1M

Compress at: H_compress = min(H_cost, H_quality, H_window)

The binding constraint determines strategy emphasis:
- H_cost binding → summarization critical, saves money every turn
- H_quality binding → summarization valuable, quality benefit > small cost penalty
- H_window binding → trim sufficient, just need to fit
- In all cases: summarize+trim is the default;
  trim-only when latency matters or mem0 covers retention

With external memory (mem0):
- Long-term facts stored externally → context only needs recent turns
- Reduces importance of in-context retention → trim-only becomes viable
- Tool outputs still accumulate → observation masking still critical
```

---

## Current Strategy (Joi)

- **Provider**: Claude via OpenRouter (10x cache discount assumed)
- **Quality**: Claude's <5% degradation is best-in-class → H_quality ≈ H_window
- **Cost penalty for summarization**: ~$0.09/turn at 200K (small in absolute terms)
- **Current**: `summarize_if_needed` at 10 messages in `graph.py` — rewrites system message and replaces message history
- **Problem**: breaks prompt caching on every summarization (both system message mutation and message list replacement)
- **Recommendation**:
  1. Observation masking (always — slows growth, extends runway)
  2. For now: summarize+trim at window limit (Claude's gentle degradation means H_quality ≈ H_window, so compression only needed near window limit)
  3. If mem0 is added: trim-only becomes viable (external memory handles retention)
- The Manus principle: "the future is parallel decomposition, not bigger windows"

---

## References

- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache preservation as #1 optimization metric
- [Don't Break the Cache (arxiv 2601.06007)](https://arxiv.org/html/2601.06007v1) — 45-80% cost reduction from cache-aware prompt design
- [The Complexity Trap (arxiv 2508.21433)](https://arxiv.org/abs/2508.21433) — observation masking beats LLM summarization at 52% lower cost
- [Anthropic: Prompt Caching](https://www.anthropic.com/news/prompt-caching) — pricing details, 5-minute TTL, prefix-based mechanics
- [PromptHub: Caching Comparison](https://www.prompthub.us/blog/prompt-caching-with-openai-anthropic-and-google-models) — multi-provider pricing and behavior comparison
- [Lost in the Middle (Liu et al., TACL 2024)](https://arxiv.org/abs/2307.03172) — U-shaped attention, >30% drop mid-context
- [Context Length Alone Hurts (Du & Tian, EMNLP 2025)](https://arxiv.org/abs/2510.05381) — 14-85% degradation even with perfect retrieval
- [Context Rot (Chroma Research, 2025)](https://research.trychroma.com/context-rot) — 18 models benchmarked, Claude decays slowest
- [RULER Benchmark (NVIDIA, COLM 2024)](https://arxiv.org/abs/2404.06654) — only 4/17 models hold quality at 32K
- [GPT-4.1 Long Context Analysis (Zep, 2025)](https://blog.getzep.com/gpt-4-1-and-o4-mini-is-openai-overselling-long-context/) — 84%→50% on complex tasks
