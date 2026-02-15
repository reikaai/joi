# Multi-Agent System Patterns

| Pattern | LLM Calls | History Isolation | When it wins |
|---------|-----------|-------------------|-------------|
| Single Agent | 2 | N/A | Few tools, short conversations |
| Swarm | 3 | None (shared) | Peer agents needing shared context |
| Supervisor | 4 | Full (delegate isolated) | Many tools, long conversations |
| Supervisor + passthrough | 3 eff. | Full | Supervisor but persona not critical on delegate responses |

## Key Insight

Supervisor's rephrase tax (~1,268 tok) buys persona consistency. Passthrough eliminates it while keeping history/schema isolation. Swarm loses on long conversations (3×H vs 2×H). Single agent loses on tool count (all schemas every call).

---

## Tradeoffs

Three axes determine which pattern wins for a given workload:

| Axis | Single Agent | Swarm | Supervisor |
|------|-------------|-------|------------|
| **Data retention** (followup quality) | Best — everything stays in context | Good — shared state, but tool call pollution grows | Worst — subagent data discarded after delegation |
| **Schema isolation** (cost per call) | Worst — all tool schemas every call | Middle — schemas partitioned by agent, but history shared | Best — delegate sees only its own schemas + task |
| **Under compaction** | Retention advantage shrinks | Retention advantage shrinks | Already "pre-compacted by design" — dominates long sessions |

### The supervisor followup problem

When a user asks a followup about data a delegate already fetched, the supervisor has none of it — the delegate's context was discarded. The chain of waste:

1. User asks followup → supervisor sees only its own summary
2. Supervisor must re-delegate → delegate re-fetches the same data
3. Delegate responds → supervisor rephrases again

Supervisor is **pre-compacted by design**: it never held the raw data in the first place. This is a feature for cost isolation but a bug for followup quality.

### Compaction equalizes patterns

Modern context management (summarization, sliding window, compaction) shrinks context over time in all patterns. Once compacted:

- Single agent's "I saw everything" advantage disappears — the raw data is gone
- Swarm's shared history gets summarized — tool call pollution is compressed away
- Supervisor already operates this way — it never had the raw data

**Schema isolation becomes the dominant factor for long sessions.** The pattern that loads fewer tool schemas per call wins on cost, and compaction doesn't change schema loading.

---

## Context Management

> For cost analysis of trim vs summarize strategies including prompt caching considerations, see [agent-patterns.md](agent-patterns.md).

The core tension: supervisor isolates too much (rephrase tax, no followup data), swarm shares too much (tool call pollution). The solution space is a spectrum of filtered handoff approaches.

### Handoff Spectrum

| Approach | Context Passed | Rephrase Tax | Followup Quality |
|----------|---------------|--------------|------------------|
| Supervisor (isolated) | Nothing | Full | Bad (re-fetch) |
| Agent-as-Tool | Task only → result only | None | Bad (re-fetch) |
| Supervisor + forward_message | Nothing → verbatim response | None | Bad (re-fetch) |
| Supervisor + state transform | Selective | None | Selective |
| Swarm (shared) | Everything | None | Good (but polluted) |

### Key Techniques

**Forward message** — `create_forward_message_tool()` from langgraph-supervisor. The supervisor forwards the subagent's response verbatim to the user, skipping the rephrase step entirely. Eliminates rephrase tax but doesn't help with followup data — the supervisor still didn't see the raw response content in a usable way.

**Agent-as-Tool** — used by Google ADK and OpenAI Agents SDK. Subagent is invoked like a tool call: receives only the task description, returns only the result string. Full isolation, zero pollution. The "rephrase" isn't a tax here — the supervisor treating the result as tool output is the natural flow.

**Observation masking** — replace older tool outputs with placeholders like `[Output from search_torrents truncated]`. Proven better than LLM-based summarization at 52% lower cost (arxiv 2508.21433). Keeps the structure of what happened without the bulk. Works in any pattern — single agent, swarm, or within a delegate's context.

**State transformation** — manual filtering on subgraph entry/exit. Control exactly what the delegate sees (input transform) and what comes back to the supervisor (output transform). LangGraph has no declarative state transformer on subgraph boundaries — the idiomatic approach is wrapping `subgraph.invoke()` in a function that filters state. This is what our `delegates.py` already does.

**Evidence filtering** — from E-mem (arxiv 2601.21714). Assistants return "logically deduced evidence" not raw data fragments. The delegate does the analytical work and returns conclusions, not dumps. Reduces supervisor context bloat while preserving semantic value.

---

## Practical Notes

**Persona-critical agents** → Agent-as-Tool is correct. The rephrase is the feature, not the bug — the supervisor maintains consistent voice across all delegate responses. Keep delegate responses brief and data-focused so the rephrase tax is small.

**Followup-heavy domains** → Consider swarm with observation masking, or enrich delegate responses with enough structured data that the supervisor can handle simple followups without re-delegation.

**Volatile data** → Re-delegation on followup is acceptable when the underlying data changes frequently (torrent availability, download queue status). The "wasted" re-fetch actually gets fresh data.

---

## References

- [Benchmarking Multi-Agent Architectures](https://blog.langchain.dev/benchmarking-multi-agent-architectures/) — LangChain, confirmed removing handoff messages from sub-agent state improves reliability
- [The Complexity Trap](https://arxiv.org/abs/2508.21433) — observation masking beats LLM summarization at 52% lower cost
- [E-mem: Master-Assistant with Evidence Filtering](https://arxiv.org/abs/2601.21714) — assistants return logically deduced evidence, not raw fragments
- [Context-Aware Multi-Agent Framework](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/) — Google ADK, agent-as-tool pattern
- [Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — Manus, practical context management
- [What Makes Multi-Agent Systems Multi-Agent](https://gist.github.com/yoavg/145decab9b793da0ee78b7a4b34e7c0e) — Yoav Goldberg, pattern taxonomy
- [Context Engineering Part 2: Multi-Agent](https://www.philschmid.de/context-engineering-agents-part-2) — Phil Schmid, implementation patterns
