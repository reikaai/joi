"""Token budget measurement for all tool variants.

Measures tool definition and system prompt token counts across all registered variants.
Run: `uv run python -m tests.eval.token_budget`
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from joi_agent_langgraph2.config import settings
from tests.eval.variants.registry import VARIANTS

EVAL_MODEL = "claude-haiku-4-5-20251001"


def measure_all_variants() -> dict[str, dict[str, int | float]]:
    """Measure token overhead for all registered variants.

    Returns dict keyed by variant name with:
      - tool_definitions_tokens: tokens used by tool schemas alone
      - system_prompt_tokens: tokens used by system prompt alone
      - total_overhead: combined tool + prompt tokens
      - delta_pct: percentage difference vs baseline tool definitions
    """
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    dummy_msg = [HumanMessage(content="test")]

    base_tokens = llm.get_num_tokens_from_messages(dummy_msg)
    logger.debug(f"Base tokens (no tools, no system prompt): {base_tokens}")

    results: dict[str, dict[str, int | float]] = {}
    for name, variant in sorted(VARIANTS.items()):
        tools = variant.tools_factory()

        total_with_tools = llm.get_num_tokens_from_messages(dummy_msg, tools=tools)
        tool_tokens = total_with_tools - base_tokens

        with_prompt = llm.get_num_tokens_from_messages(
            [SystemMessage(content=variant.persona), *dummy_msg],
            tools=tools,
        )
        prompt_only = llm.get_num_tokens_from_messages(
            [SystemMessage(content=variant.persona), *dummy_msg],
        )

        results[name] = {
            "tool_definitions_tokens": tool_tokens,
            "system_prompt_tokens": prompt_only - base_tokens,
            "total_overhead": with_prompt - base_tokens,
            "delta_pct": 0.0,
        }

    baseline_tools = results.get("baseline", {}).get("tool_definitions_tokens", 0)
    if baseline_tools:
        for r in results.values():
            r["delta_pct"] = (r["tool_definitions_tokens"] - baseline_tools) / baseline_tools * 100

    return results


def print_table(results: dict[str, dict[str, int | float]]) -> None:
    header = f"{'Variant':<20s} {'Tools':>6s} {'Prompt':>7s} {'Total':>6s} {'Delta':>8s}"
    print(header)
    print("-" * len(header))
    for name in sorted(results):
        r = results[name]
        print(
            f"{name:<20s} "
            f"{r['tool_definitions_tokens']:>6.0f} "
            f"{r['system_prompt_tokens']:>7.0f} "
            f"{r['total_overhead']:>6.0f} "
            f"{r['delta_pct']:>+7.1f}%"
        )


def check_budget(results: dict[str, dict[str, int | float]], threshold_pct: float = 10.0) -> bool:
    applike = results.get("applike")
    if not applike:
        logger.warning("No applike variant found")
        return False

    delta = applike["delta_pct"]
    within = abs(delta) <= threshold_pct
    status = "PASS" if within else "FAIL"
    print(f"\nBudget check: applike tool definitions {delta:+.1f}% vs baseline ({status}, threshold: +/-{threshold_pct}%)")
    return within


if __name__ == "__main__":
    results = measure_all_variants()
    print_table(results)
    check_budget(results)
