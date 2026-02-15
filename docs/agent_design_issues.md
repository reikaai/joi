# Agent Design Issues & Decisions

## Anthropic Prompt Caching: Why Direct API

### Problem
Prompt caching via `ChatOpenAI` + OpenRouter always shows 0 cache metrics. Three root causes:

### Root Cause 1: ChatOpenAI Strips `cache_control`
LangChain explicitly rejected adding support ([langchain#33757](https://github.com/langchain-ai/langchain/issues/33757)).

`langchain_openai/chat_models/base.py` uses allowlist filtering:

- **Tool definitions** (`convert_to_openai_tool()` in `langchain_core/utils/function_calling.py:410-416`):
  ```python
  oai_function = {k: v for k, v in function.items() if k in {"name", "description", "parameters", "strict"}}
  ```
  → `cache_control` on tool dict: **stripped**

- **ToolMessage** (`base.py:356-361`):
  ```python
  supported_props = {"content", "role", "tool_call_id"}
  ```
  → extra fields: **stripped**

- **Content blocks** (`_format_message_content()`, `base.py:227-285`):
  → Dict content blocks pass through **intact** — only place `cache_control` survives

### Root Cause 2: ChatOpenAI Drops Cache Metrics
`_create_usage_metadata` only reads `cached_tokens`, never `cache_write_tokens`.

### Root Cause 3: OpenRouter Caching Unreliable
Multiple community reports of caching failing to activate even when markers are present.

### Options Evaluated

| Option | Status | Why |
|--------|--------|-----|
| `ChatOpenAI` + OpenRouter | **Dead end** | Tool cache_control stripped, response metrics dropped |
| `ChatAnthropic` + OpenRouter | **Broken** | URL duplication bug ([langchain#31325](https://github.com/langchain-ai/langchain/issues/31325)) |
| `langchain-openrouter` (`ChatOpenRouter`) | **No caching** | v0.0.2, extends `BaseChatModel`, zero `cache_control` code, uses `convert_to_openai_tool()` which strips it |
| **`ChatAnthropic` + direct Anthropic API** | **Chosen** | Native caching, proper metrics |

### Decision
Switch to `ChatAnthropic` with direct Anthropic API. This is the only path that:
- Preserves `cache_control` on tools, system messages, and content blocks
- Returns proper `cache_read_input_tokens` and `cache_creation_input_tokens` in responses
- Populates `InputTokenDetails(cache_read=..., cache_creation=...)` in LangChain's `usage_metadata`
