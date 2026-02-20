import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import testing as t

from joi_agent_langgraph2.config import settings
from tests.experiment.conftest import EVAL_MODEL, FIXED_TIMESTAMP, ZERO_PERSONA
from tests.experiment.scenarios import SCENARIOS
from tests.experiment.variants.registry import VARIANTS


@pytest.mark.langsmith
@pytest.mark.experiment
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(VARIANTS), ids=list(VARIANTS))
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
async def test_scenario(variant_name, scenario, run_id, jsonl_writer):
    variant = VARIANTS[variant_name]
    llm = ChatAnthropic(model=EVAL_MODEL, api_key=settings.anthropic_api_key)
    model = llm.bind_tools(variant.tools_factory())

    t.log_inputs(
        {
            "prompt": scenario.prompt,
            "variant": variant_name,
            "category": scenario.category,
            "run_id": run_id,
            "fixed_timestamp": FIXED_TIMESTAMP,
        }
    )

    response = await model.ainvoke(
        [
            SystemMessage(content=ZERO_PERSONA),
            HumanMessage(content=f"[{FIXED_TIMESTAMP}]\n{scenario.prompt}"),
        ]
    )

    # Extract response text (handle both str and list content)
    content = response.content
    if isinstance(content, list):
        text_parts = [
            c["text"]
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        response_text = " ".join(text_parts)
    else:
        response_text = content or ""

    tool_calls = [
        {"name": tc["name"], "args": tc["args"]} for tc in response.tool_calls
    ]
    usage = response.usage_metadata or {}

    t.log_outputs({"response_text": response_text, "tool_calls": tool_calls})
    t.log_feedback(key="variant", value=variant_name)
    t.log_feedback(key="run_id", value=run_id)
    t.log_feedback(key="category", value=scenario.category)
    t.log_feedback(key="input_tokens", value=usage.get("input_tokens", 0))
    t.log_feedback(key="output_tokens", value=usage.get("output_tokens", 0))

    jsonl_writer.write_result(
        variant=variant_name,
        scenario_id=scenario.id,
        category=scenario.category,
        prompt=scenario.prompt,
        response_text=response_text,
        tool_calls=tool_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )
    # NO assertions — capture only. Evaluation happens in Phase 10.
