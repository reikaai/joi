# Context Management Cost Framework

Decision framework for evaluating trim vs summarize strategies, accounting for prompt caching economics across providers.

---

## Prompt Caching Fundamentals

LLM providers cache the KV-cache of prompt prefixes. Key properties:

- **Prefix-based**: only the longest matching prefix from the start of the prompt is cached
- **Append-only friendly**: adding messages at the end preserves the cache; inserting/deleting/reordering breaks it
- **What breaks caching**: system message mutation, message deletion or reordering, timestamps injected into prompts, summarization that replaces message history
- **TTL**: typically 5 minutes (Anthropic), varies by provider

### Provider Pricing (as of 2025)

| Provider | Input $/MTok | Cached $/MTok | Discount (D) |
|----------|-------------|---------------|--------------|
| Claude Sonnet 4 | $3.00 | $0.30 | 10x |
| GPT-4o | $2.50 | $1.25 | 2x |
| Gemini 2.0 Flash | $0.10 | $0.025 | 4x |

D = c_uncached / c_cached — the cache discount ratio. Higher D means caching saves more per token.

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

## Reset Strategies Compared

| Strategy | Cache Break | Info Loss | Extra LLM Call | When to Use |
|----------|-----------|-----------|----------------|-------------|
| Trim (drop oldest) | Yes | Full (on dropped messages) | No | Default — cheapest, simplest |
| Summarize | Yes | Partial | Yes (+ latency) | Followup quality on old context matters |
| Observation masking | **No** | Partial (tool outputs only) | No | Between resets — slows prefix growth |

**Observation masking** is the only strategy that preserves the cache. Replace bulky tool outputs with `[Output truncated]` while keeping message structure intact. The prefix remains unchanged, so the cache holds. Use it as a first line of defense before resorting to trim/summarize.

---

## Decision Framework

```
1. Look up provider's cache discount ratio: D = c_uncached / c_cached
2. Estimate realistic compression ratio: R (typically 3-5x)
3. Per-turn decision:
   - If R < D → don't summarize for cost reasons (caching is always cheaper)
   - If R > D → summarization can save per-turn cost
4. Lifecycle decision:
   - If context window is the binding constraint → trim at window limit
   - If cost is the binding constraint → summarize at interval:
     H_threshold = K × c_uncached / (c_cached - c_uncached/R)
5. Always:
   - Use observation masking first (no cache break, no LLM call)
   - Trim at context window limit as safety net regardless of strategy
```

---

## Current Strategy (Joi)

- **Provider**: Claude via OpenRouter (10x cache discount assumed)
- **Current**: `summarize_if_needed` at 10 messages in `graph.py` — rewrites system message and replaces message history
- **Problem**: breaks prompt caching on every summarization (both system message mutation and message list replacement)
- **Per framework**: R < D (3-5x < 10x) → summarization is **more expensive** per-turn than cached full history
- **Recommendation**: switch to append-only + observation masking + trim at window limit
  1. Never mutate system message after first turn
  2. Mask old tool outputs once they exceed a size threshold
  3. Hard trim (drop oldest messages) when approaching context window limit
  4. No summarization LLM calls needed

---

## References

- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache preservation as #1 optimization metric
- [Don't Break the Cache (arxiv 2601.06007)](https://arxiv.org/html/2601.06007v1) — 45-80% cost reduction from cache-aware prompt design
- [The Complexity Trap (arxiv 2508.21433)](https://arxiv.org/abs/2508.21433) — observation masking beats LLM summarization at 52% lower cost
- [Anthropic: Prompt Caching](https://www.anthropic.com/news/prompt-caching) — pricing details, 5-minute TTL, prefix-based mechanics
- [PromptHub: Caching Comparison](https://www.prompthub.us/blog/prompt-caching-with-openai-anthropic-and-google-models) — multi-provider pricing and behavior comparison
