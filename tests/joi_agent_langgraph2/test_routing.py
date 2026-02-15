import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from joi_agent_langgraph2.config import settings

# --- Stub tools (mirror real signatures + docstrings, no implementation) ---


@tool
def delegate_media(query: str) -> str:
    """Query or manage media: what's downloaded, active torrents, search/download movies/shows.

    Use for ANY question about movies, shows, or torrents.
    """
    return ""


@tool
def recall(query: str) -> str:
    """Recall personal facts/preferences previously saved about the user.

    NOT for media, downloads, or torrents — use delegate_media for those.
    """
    return ""


@tool
def remember(fact: str) -> str:
    """Remember a fact or preference for the user. Use this to store information the user wants you to remember."""
    return ""


TOOLS = [delegate_media, recall, remember]
PERSONA = settings.persona_path.read_text()


@pytest.fixture
def model_with_tools():
    llm = ChatOpenAI(
        model=settings.llm_model.replace("openai/", ""),
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        temperature=0,
    )
    return llm.bind_tools(TOOLS)


ROUTING_CASES = [
    ("which movies we have downloaded?", "delegate_media"),
    ("any active torrents?", "delegate_media"),
    ("find me a thriller movie", "delegate_media"),
    ("what's downloading right now?", "delegate_media"),
    ("what's my favorite color?", "recall"),
    ("do you remember my dog's name?", "recall"),
    ("my birthday is March 5th", "remember"),
]


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_tool", ROUTING_CASES, ids=[q for q, _ in ROUTING_CASES])
async def test_tool_routing(model_with_tools, query: str, expected_tool: str):
    system_msg = SystemMessage(content=PERSONA)
    response = await model_with_tools.ainvoke([system_msg, HumanMessage(content=query)])
    tool_calls = response.tool_calls
    assert tool_calls, f"No tool called for: {query}"
    assert tool_calls[0]["name"] == expected_tool, f"Expected {expected_tool}, got {tool_calls[0]['name']} for: {query}"
