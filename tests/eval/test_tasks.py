import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith import testing as t

import tests.eval.variants.tasks_baseline  # noqa: F401 -- trigger registration
from joi_agent_langgraph2.config import settings
from tests.eval.conftest import Scenario, load_scenarios, record_eval_result
from tests.eval.evaluators import evaluate_tool_calls
from tests.eval.variants.registry import VARIANTS, ToolVariant

EVAL_MODEL = "claude-haiku-4-5-20251001"

CACHE_DIR = Path(__file__).parent / "cache"


def _cache_path(variant_name: str, scenario_id: str) -> Path:
    safe_id = scenario_id.replace(":", "_").replace("/", "_")
    return CACHE_DIR / variant_name / f"{safe_id}.json"


def _serialize_response(response: AIMessage) -> dict:
    tool_calls = [
        {"name": tc["name"], "args": tc["args"], "id": tc.get("id", "")}
        for tc in response.tool_calls
    ]
    usage = response.usage_metadata
    content = response.content
    if isinstance(content, list):
        text_parts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
        content = " ".join(text_parts)
    return {
        "content": content if isinstance(content, str) else "",
        "tool_calls": tool_calls,
        "usage_metadata": {
            "input_tokens": usage.get("input_tokens", 0) if usage else 0,
            "output_tokens": usage.get("output_tokens", 0) if usage else 0,
            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
        },
    }


def _deserialize_response(data: dict) -> AIMessage:
    return AIMessage(
        content=data.get("content", ""),
        tool_calls=data.get("tool_calls", []),
        usage_metadata=data.get("usage_metadata"),
    )


async def invoke_variant(variant: ToolVariant, prompt: str, variant_name: str, scenario_id: str) -> AIMessage:
    cache_mode = os.environ.get("LANGSMITH_TEST_CACHE", "")
    cp = _cache_path(variant_name, scenario_id)

    # Cache read: return cached response if available
    if cache_mode == "read":
        if cp.exists():
            data = json.loads(cp.read_text())
            return _deserialize_response(data)
        # Fall through to real call if cache miss, then save

    # Real LLM call
    llm = ChatAnthropic(  # ty: ignore[missing-argument]
        model=EVAL_MODEL,
        api_key=settings.anthropic_api_key,
    )
    model = llm.bind_tools(variant.tools_factory())
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    response = await model.ainvoke([
        SystemMessage(content=variant.persona),
        HumanMessage(content=f"[{ts}]\n{prompt}"),
    ])

    # Cache write: save response
    if cache_mode in ("read", "write"):
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(_serialize_response(response), indent=2))

    return response


# ── Parametrize helpers ──────────────────────────────────────────────────────

_positive_scenarios = load_scenarios("tasks_positive")
_negative_scenarios = load_scenarios("tasks_negative")
_variant_names = list(VARIANTS.keys())


@pytest.mark.langsmith
@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", _variant_names, ids=_variant_names)
@pytest.mark.parametrize(
    "scenario",
    _positive_scenarios,
    ids=[s.id for s in _positive_scenarios],
)
async def test_positive(variant_name: str, scenario: Scenario, eval_results: dict):
    variant = VARIANTS[variant_name]

    t.log_inputs({"prompt": scenario.prompt, "variant": variant_name, "category": scenario.category})
    t.log_reference_outputs({"expected_tool": scenario.expected_tool, "min_calls": scenario.min_calls})

    response = await invoke_variant(variant, scenario.prompt, variant_name, scenario.id)
    result = evaluate_tool_calls(response, scenario, variant)

    resp_content = response.content
    if isinstance(resp_content, list):
        text_parts = [c["text"] for c in resp_content if isinstance(c, dict) and c.get("type") == "text"]
        response_text = " ".join(text_parts)
    else:
        response_text = resp_content or ""

    t.log_outputs({"response_text": response_text, "tool_call_names": result.tool_call_names, "call_count": result.call_count})
    t.log_feedback(key="correct_tool", score=result.correct_tool_score)
    t.log_feedback(key="correct_count", score=result.correct_count_score)
    t.log_feedback(key="input_tokens", value=result.input_tokens)
    t.log_feedback(key="output_tokens", value=result.output_tokens)
    t.log_feedback(key="total_tokens", value=result.total_tokens)

    record_eval_result(
        eval_results,
        variant_name,
        correct_tool_score=result.correct_tool_score,
        correct_count_score=result.correct_count_score,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        scenario_id=scenario.id,
        category=scenario.category,
    )

    assert result.passed, result.failure_message


@pytest.mark.langsmith
@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", _variant_names, ids=_variant_names)
@pytest.mark.parametrize(
    "scenario",
    _negative_scenarios,
    ids=[s.id for s in _negative_scenarios],
)
async def test_negative(variant_name: str, scenario: Scenario, eval_results: dict):
    variant = VARIANTS[variant_name]

    t.log_inputs({"prompt": scenario.prompt, "variant": variant_name, "category": "negative"})
    t.log_reference_outputs({"expected_tool_calls": 0})

    response = await invoke_variant(variant, scenario.prompt, variant_name, scenario.id)

    # Count scheduling tool calls
    schedule_names = variant.schedule_tool_names or [variant.schedule_tool_name]
    schedule_calls = [tc for tc in response.tool_calls if tc["name"] in schedule_names]
    if variant.schedule_action:
        schedule_calls = [c for c in schedule_calls if c["args"].get("action") == variant.schedule_action]

    usage = response.usage_metadata or {}
    no_false_trigger = 1.0 if len(schedule_calls) == 0 else 0.0

    t.log_outputs({"schedule_call_count": len(schedule_calls)})
    t.log_feedback(key="no_false_trigger", score=no_false_trigger)
    t.log_feedback(key="input_tokens", value=usage.get("input_tokens", 0))
    t.log_feedback(key="output_tokens", value=usage.get("output_tokens", 0))
    t.log_feedback(key="total_tokens", value=usage.get("total_tokens", 0))

    record_eval_result(
        eval_results,
        variant_name,
        correct_tool_score=no_false_trigger,
        correct_count_score=1.0,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        scenario_id=scenario.id,
        category="negative",
    )

    assert len(schedule_calls) == 0, (
        f"[{variant_name}] Expected 0 scheduling calls for negative scenario '{scenario.id}', "
        f"got {len(schedule_calls)}"
    )


# ── Round-trip serialization test ──────────────────────────────────────────────


def test_serialize_deserialize_roundtrip():
    # Test list-type content (text + tool_use dicts)
    list_content = [
        {"type": "text", "text": "I'll set that reminder."},
        {"type": "tool_use", "id": "toolu_123", "name": "schedule_task", "input": {}},
    ]
    msg_list = AIMessage(
        content=list_content,
        tool_calls=[{"name": "schedule_task", "args": {"task": "test"}, "id": "toolu_123"}],
    )
    serialized = _serialize_response(msg_list)
    assert serialized["content"] == "I'll set that reminder."
    assert len(serialized["tool_calls"]) == 1
    assert serialized["tool_calls"][0]["name"] == "schedule_task"

    deserialized = _deserialize_response(serialized)
    assert deserialized.content == "I'll set that reminder."
    assert len(deserialized.tool_calls) == 1

    # Test plain string content (no regression)
    msg_str = AIMessage(
        content="Simple string response",
        tool_calls=[],
    )
    serialized_str = _serialize_response(msg_str)
    assert serialized_str["content"] == "Simple string response"

    deserialized_str = _deserialize_response(serialized_str)
    assert deserialized_str.content == "Simple string response"
