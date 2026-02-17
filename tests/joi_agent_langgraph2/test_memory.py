from unittest.mock import MagicMock

import pytest

from joi_agent_langgraph2.memory import create_memory_tools

FAKE_CONFIG = {"configurable": {"user_id": "test-user-42"}}


@pytest.fixture
def mock_mem0():
    m = MagicMock()
    m.add = MagicMock(return_value=None)
    m.search = MagicMock(return_value={"results": [{"memory": "likes blue"}, {"memory": "speaks Russian"}]})
    return m


@pytest.fixture
def memory_tools(mock_mem0):
    return {t.name: t for t in create_memory_tools(mock_mem0)}


@pytest.mark.asyncio
async def test_remember_calls_mem0_add(mock_mem0, memory_tools):
    result = await memory_tools["remember"].ainvoke({"fact": "prefers dark mode"}, config=FAKE_CONFIG)
    assert "Remembered" in result
    mock_mem0.add.assert_called_once_with("prefers dark mode", user_id="test-user-42")


@pytest.mark.asyncio
async def test_recall_returns_formatted_memories(mock_mem0, memory_tools):
    result = await memory_tools["recall"].ainvoke({"query": "color"}, config=FAKE_CONFIG)
    assert "likes blue" in result
    assert "speaks Russian" in result
    mock_mem0.search.assert_called_once_with("color", user_id="test-user-42")


@pytest.mark.asyncio
async def test_recall_no_results(mock_mem0, memory_tools):
    mock_mem0.search.return_value = {"results": []}
    result = await memory_tools["recall"].ainvoke({"query": "nonexistent"}, config=FAKE_CONFIG)
    assert "No relevant memories" in result
