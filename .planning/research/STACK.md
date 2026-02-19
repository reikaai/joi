# Technology Stack

**Project:** Joi Agent Tool Interface Eval Infrastructure
**Researched:** 2026-02-19

## Recommended Stack

### Core Eval Framework: pytest + LangSmith pytest plugin

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | >=8.4.2 | Test runner and eval harness | Already in project; parametrize gives us variant x case matrix for free |
| langsmith[pytest] | >=0.7.4 | Track eval experiments, cache LLM calls, compare runs | Native pytest integration via `@pytest.mark.langsmith`; experiment tracking with zero infra; caching cuts repeat eval cost 10x; already partially in stack (langsmith is a langchain dep) |
| agentevals | >=0.0.9 | Trajectory matching evaluators | LangChain-native; provides strict/unordered/subset trajectory matchers + LLM-as-judge for trajectories; MIT license; tiny dependency |

**Confidence: HIGH** -- LangSmith pytest plugin verified at v0.7.4 (released 2026-02-18), agentevals at v0.0.9 (2025-07-24). Both from LangChain org, actively maintained. pytest already in stack.

### Observability: Langfuse (already installed)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| langfuse | >=3.14.3 | Production trace scoring, cost tracking per variant | Already in pyproject.toml; v3 SDK rewrite (June 2025) added tool call visualization + dataset experiments; self-hostable; can score traces post-hoc with custom metrics |

**Confidence: HIGH** -- Already a project dependency. v3.14.3 verified on PyPI (2026-02-17).

### Statistical Analysis

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| scipy | >=1.12 | Bootstrap confidence intervals, statistical significance | `scipy.stats.bootstrap` for BCa confidence intervals on pass rates; `scipy.stats.fisher_exact` for small-sample binary comparisons; standard, no new deps needed (numpy transitive) |

**Confidence: HIGH** -- scipy.stats.bootstrap is stable API since 1.7. Standard scientific Python.

### Metrics Collection

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tiktoken | >=0.7 | Token counting for cost metrics | Anthropic tokens approximate; tiktoken cl100k gives ballpark for cost comparison across variants |
| anthropic | (via langchain-anthropic) | Usage metadata extraction | `response.usage_metadata` gives exact input/output token counts per call |

**Confidence: MEDIUM** -- tiktoken is OpenAI's tokenizer, not Anthropic's. For relative comparison between variants (not absolute cost), it's sufficient. Anthropic's own usage metadata from API responses is more accurate for absolute numbers.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openevals | >=0.1.3 | LLM-as-judge evaluators (correctness, hallucination) | When adding semantic quality checks beyond tool call correctness |
| pytest-xdist | >=3.0 | Parallel test execution | When eval matrix exceeds 100 cases and wall-clock time matters |
| tabulate | >=0.9 | Formatted result tables in terminal output | For human-readable eval reports during development |

**Confidence: MEDIUM** -- openevals v0.1.3 verified (2025-12-18). pytest-xdist is standard.

## What NOT to Use

| Category | Rejected | Why Not |
|----------|----------|---------|
| Eval framework | DeepEval | Heavy dependency (requires `deepeval` server process); ToolCorrectnessMetric and ToolUseMetric use GPT-4o by default (extra cost + different model's judgment); the project already has LangSmith + Langfuse for tracking; adding a third observability layer creates confusion |
| Eval framework | Promptfoo | Node.js CLI tool; the project is pure Python; YAML config adds indirection vs. pytest parametrize which is already working; better suited for prompt comparison than tool interface comparison |
| Eval framework | Braintrust | SaaS-only for core features; adds vendor lock-in; LangSmith covers the same ground and is already integrated via LangChain |
| Eval framework | Ragas | Focused on RAG evaluation (retrieval, generation); wrong domain for tool-calling eval |
| Custom eval harness | Building from scratch | The existing test already does 80% of what's needed; wrapping it with LangSmith tracking + agentevals trajectory matchers gets the remaining 20% without new infrastructure |

## How the Stack Fits Together

```
pytest (runner)
  |
  +-- @pytest.mark.langsmith (experiment tracking + caching)
  |     |
  |     +-- langsmith experiments dashboard (compare variants over time)
  |
  +-- @pytest.mark.eval (existing marker, keep for local-only runs)
  |
  +-- agentevals trajectory matchers (structured tool call assertions)
  |     |
  |     +-- strict match: exact tool sequence
  |     +-- unordered match: right tools, any order
  |     +-- subset match: at least these tools called
  |
  +-- Custom metrics (collected per test case):
  |     +-- tool_call_count (deterministic)
  |     +-- token_usage (from API response)
  |     +-- correct_args_ratio (deterministic)
  |     +-- recurring_detected (deterministic)
  |     +-- stagger_correctness (deterministic)
  |
  +-- scipy.stats.bootstrap (post-run analysis)
        |
        +-- confidence intervals on pass rates per variant
        +-- pairwise significance tests
```

## Installation

```bash
# Core eval stack (new additions only)
uv add --dev "langsmith[pytest]>=0.7.4"
uv add --dev "agentevals>=0.0.9"

# Statistical analysis (likely already transitive, but pin explicitly)
uv add --dev "scipy>=1.12"

# Optional: result formatting
uv add --dev "tabulate>=0.9"
```

Note: `langfuse` is already in production deps. `langchain-anthropic` already provides access to Anthropic usage metadata. No new production dependencies needed.

## Key Configuration

```bash
# .env additions for eval runs
LANGSMITH_API_KEY=...           # For experiment tracking
LANGSMITH_PROJECT=joi-tool-eval # Project name in LangSmith
LANGSMITH_TEST_CACHE=.cache/langsmith  # Cache LLM responses between runs
```

## Migration from Current Eval

The existing `test_task_scheduling_eval.py` (579 lines) is a solid foundation. Migration path:

1. Add `@pytest.mark.langsmith` alongside existing `@pytest.mark.eval`
2. Use `t.log_inputs()` / `t.log_outputs()` / `t.log_feedback()` for structured tracking
3. Replace raw assertions with agentevals trajectory matchers where appropriate
4. Add token cost extraction from `response.usage_metadata`
5. Add post-run statistical analysis script using scipy bootstrap

No rewrite needed -- incremental enhancement of existing infrastructure.

## Sources

- LangSmith pytest docs: https://docs.langchain.com/langsmith/pytest (MEDIUM -- verified via official docs)
- LangSmith PyPI: https://pypi.org/project/langsmith/ -- v0.7.4, 2026-02-18 (HIGH)
- agentevals PyPI: https://pypi.org/project/agentevals/ -- v0.0.9, 2025-07-24 (HIGH)
- agentevals GitHub: https://github.com/langchain-ai/agentevals (HIGH)
- Langfuse PyPI: https://pypi.org/project/langfuse/ -- v3.14.3, 2026-02-17 (HIGH)
- DeepEval tool correctness: https://deepeval.com/docs/metrics-tool-correctness (MEDIUM -- verified API)
- Anthropic agent evals guide: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (HIGH)
- Anthropic tool writing guide: https://www.anthropic.com/engineering/writing-tools-for-agents (HIGH)
- LangChain evaluating deep agents: https://blog.langchain.com/evaluating-deep-agents-our-learnings/ (HIGH)
- openevals PyPI: https://pypi.org/project/openevals/ -- v0.1.3, 2025-12-18 (HIGH)
- scipy bootstrap: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html (HIGH)
