# Anthropic Prompt Caching

## How it works

Two cache breakpoints via middleware in `src/joi_agent_langgraph2/graph.py`:

1. **System prompt** — `anthropic_cache_system_prompt` middleware injects `cache_control` into the system message content block directly
2. **Last message** — `AnthropicPromptCachingMiddleware()` injects `cache_control` via `model_settings` → `kwargs.pop("cache_control")` in `ChatAnthropic._generate()`, applied to the last user message

Both require `{"type": "ephemeral", "ttl": "5m"}` — the `ttl` field is mandatory (Anthropic silently ignores `cache_control` without it).

## Minimum token thresholds

Prompt caching only activates when the **cacheable prefix** (everything before the breakpoint) exceeds the model's minimum token count.

| Model | Min tokens | Source |
|-------|-----------|--------|
| Claude Haiku 3.5 | 2,048 | [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |
| **Claude Haiku 4.5** | **4,096** | [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |
| Claude Sonnet 3.7–4.5 | 1,024 | [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |
| Claude Opus 4–4.6 | 4,096 | [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |

Our system prompt (~1,000 tokens) + tools (~500 tokens) = ~1,500 tokens — **below Haiku 4.5's 4,096 minimum**. The system prompt breakpoint alone will never trigger caching on Haiku 4.5.

The last-message breakpoint kicks in once total prompt tokens exceed 4,096 — roughly after 5–8 back-and-forth exchanges.

## Implications for our agent

- **Short conversations** (1–3 exchanges): no caching benefit on Haiku 4.5
- **Longer conversations** (5+ exchanges): last-message breakpoint caches the growing prefix, reducing cost on subsequent turns
- **If we switch to Sonnet**: system prompt breakpoint alone would work (1,500 > 1,024 minimum)

## Debugging with LangSmith

Check the `usage` field in LLM run traces:

```
cache_creation_input_tokens > 0  →  cache write happened (first request)
cache_read_input_tokens > 0      →  cache hit (subsequent requests within TTL)
```

If both are 0, the prompt is under the minimum token threshold for the model.

## References

- [Anthropic Prompt Caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [langchain-anthropic cache_control handling](https://github.com/langchain-ai/langchain/blob/master/libs/partners/anthropic/langchain_anthropic/chat_models.py) — `kwargs.pop("cache_control")` at line ~1070
- [AnthropicPromptCachingMiddleware](https://github.com/langchain-ai/langchain/blob/master/libs/partners/anthropic/langchain_anthropic/middleware/prompt_caching.py)
- [LangChain issue #33635](https://github.com/langchain-ai/langchain/issues/33635) — LangGraph create_agent caching support
