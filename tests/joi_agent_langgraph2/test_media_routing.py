from typing import Annotated

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import Field

from joi_agent_langgraph2.config import settings

# --- Stub tools (mirror real MCP tool signatures + docstrings) ---


@tool
def list_torrents(
    filter_expr: Annotated[
        str | None,
        Field(description="JMESPath. Downloaded: progress==`100` (NOT status). Active: status=='downloading'. Text: search(@, 'text')"),
    ] = None,
    fields: Annotated[
        list[str] | None,
        Field(
            description="Columns (id auto-incl.). Recommended: name,total_size."
            " Drop columns implied by filter (e.g. progress if progress==100)"
        ),
    ] = None,
    sort_by: Annotated[str | None, Field(description="Sort field, - prefix for desc")] = None,
    limit: Annotated[int, Field()] = 25,
    offset: Annotated[int, Field()] = 0,
) -> str:
    """List torrents (CSV). No filter = all.
    Fields: name, status, progress, eta, total_size, error_string, download_speed, file_count.
    CRITICAL: downloaded/completed = progress==`100` ONLY.
    NEVER use status for downloaded. status=='downloading' = ACTIVELY in-progress."""
    return ""


@tool
def add_torrent(url: str, download_dir: str | None = None) -> str:
    """Add a torrent by URL or magnet link."""
    return ""


@tool
def search_movies(query: str) -> str:
    """Search for movies on TMDB."""
    return ""


@tool
def search_torrents(query: str) -> str:
    """Search for torrents on Jackett."""
    return ""


TOOLS = [list_torrents, add_torrent, search_movies, search_torrents]
MEDIA_PERSONA = settings.media_persona_path.read_text()


@pytest.fixture
def media_model():
    llm = ChatOpenAI(
        model=settings.llm_model.replace("openai/", ""),
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        temperature=0,
    )
    return llm.bind_tools(TOOLS)


FILTER_CASES = [
    pytest.param(
        "what did we download",
        {"must_contain": ["progress", "100"]},
        id="downloaded-uses-progress",
    ),
    pytest.param(
        "which movies we have downloaded?",
        {"must_contain": ["progress", "100"]},
        id="downloaded-movies-uses-progress",
    ),
    pytest.param(
        "what's downloading right now?",
        {"must_contain": ["status", "downloading"]},
        id="downloading-uses-status",
    ),
]


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("query,checks", FILTER_CASES)
async def test_media_filter_expr(media_model, query: str, checks: dict):
    response = await media_model.ainvoke(
        [SystemMessage(content=MEDIA_PERSONA), HumanMessage(content=query)]
    )
    tool_calls = response.tool_calls
    assert tool_calls, f"No tool called for: {query}"
    assert tool_calls[0]["name"] == "list_torrents", (
        f"Expected list_torrents, got {tool_calls[0]['name']} for: {query}"
    )

    filter_expr = tool_calls[0]["args"].get("filter_expr", "")
    assert filter_expr, f"No filter_expr for: {query}"

    for term in checks.get("must_contain", []):
        assert term in filter_expr, (
            f"filter_expr missing '{term}': got '{filter_expr}' for: {query}"
        )
    for term in checks.get("must_not_contain", []):
        assert term not in filter_expr, (
            f"filter_expr should NOT contain '{term}': got '{filter_expr}' for: {query}"
        )

    fields = tool_calls[0]["args"].get("fields")
    assert fields, f"LLM should use fields param for projection, got None for: {query}"
