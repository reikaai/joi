import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from joi_agent_langgraph2.graph import truncate_tool_results


@pytest.mark.unit
def test_masks_old_tool_results():
    msgs = [HumanMessage(content="hi")]
    for i in range(15):
        msgs.append(ToolMessage(content=f"result-{i}", tool_call_id=f"tc-{i}", id=f"tm-{i}", status="success"))

    result = truncate_tool_results(msgs, keep=10)

    assert len(result) == 16
    for i in range(5):
        assert result[i + 1].content == "[Output truncated]"
    for i in range(5, 15):
        assert result[i + 1].content == f"result-{i}"


@pytest.mark.unit
def test_preserves_non_tool_messages():
    msgs = [
        HumanMessage(content="hello"),
        AIMessage(content="world"),
        ToolMessage(content="tool-out", tool_call_id="tc-0", id="tm-0", status="success"),
        HumanMessage(content="follow-up"),
    ]
    result = truncate_tool_results(msgs, keep=10)

    assert result[0].content == "hello"
    assert result[1].content == "world"
    assert result[2].content == "tool-out"
    assert result[3].content == "follow-up"


@pytest.mark.unit
def test_noop_when_under_threshold():
    msgs = []
    for i in range(5):
        msgs.append(ToolMessage(content=f"r-{i}", tool_call_id=f"tc-{i}", id=f"tm-{i}", status="success"))

    result = truncate_tool_results(msgs, keep=10)

    for i in range(5):
        assert result[i].content == f"r-{i}"


@pytest.mark.unit
def test_preserves_tool_call_id_and_status():
    msgs = []
    for i in range(12):
        msgs.append(ToolMessage(content=f"r-{i}", tool_call_id=f"tc-{i}", id=f"tm-{i}", status="success"))

    result = truncate_tool_results(msgs, keep=10)

    masked = result[0]
    assert masked.content == "[Output truncated]"
    assert masked.tool_call_id == "tc-0"
    assert masked.id == "tm-0"
    assert masked.status == "success"


@pytest.mark.unit
def test_empty_messages():
    assert truncate_tool_results([]) == []
