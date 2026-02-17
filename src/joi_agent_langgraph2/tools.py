import asyncio
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

from joi_agent_langgraph2.config import settings

MCP_SERVERS = {
    "tmdb": {
        "url": f"{settings.mcp_url}/tmdb/",
        "transport": "streamable_http",
    },
    "transmission": {
        "url": f"{settings.mcp_url}/transmission/",
        "transport": "streamable_http",
    },
    "jackett": {
        "url": f"{settings.mcp_url}/jackett/",
        "transport": "streamable_http",
    },
}

MUTATION_TOOLS = {
    "add_torrent",
    "remove_torrent",
    "pause_torrent",
    "resume_torrent",
    "set_file_priorities",
}

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 1.0


def _wrap_with_progress(tool: BaseTool, *, retries: int = MAX_RETRY_ATTEMPTS) -> BaseTool:
    original_coro = tool.coroutine  # type: ignore[union-attr]
    max_attempts = max(retries, 1)

    async def _wrapped(*, config: RunnableConfig = None, **kwargs: Any) -> str:  # type: ignore[assignment]
        from langgraph.config import get_stream_writer

        try:
            writer = get_stream_writer()
        except Exception:
            writer = None

        args_str = ", ".join(f"{v}" for v in kwargs.values())

        if config is not None:
            kwargs["config"] = config
        display = f"{tool.name}({args_str})" if args_str else tool.name

        if writer:
            writer({"type": "tool_start", "tool": tool.name, "display": display})

        last_err: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = await original_coro(**kwargs)
                if writer:
                    writer({"type": "tool_done", "tool": tool.name})
                return result
            except Exception as e:
                last_err = e
                if attempt < max_attempts:
                    delay = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(f"{tool.name} attempt {attempt} failed: {e}, retrying in {delay}s")
                    if writer:
                        writer({"type": "tool_retry", "tool": tool.name, "attempt": attempt, "error": str(e)})
                    await asyncio.sleep(delay)

        if writer:
            writer({"type": "tool_error", "tool": tool.name, "error": str(last_err)})
        raise last_err  # type: ignore[misc]

    tool.coroutine = _wrapped  # type: ignore[union-attr]
    return tool


RETRY_TOOLS = {"delegate_media"}


def prepare_tools(tools: list) -> list:
    return [
        _wrap_with_progress(t, retries=MAX_RETRY_ATTEMPTS if t.name in RETRY_TOOLS else 0)
        if isinstance(t, BaseTool)
        else t
        for t in tools
    ]


def create_media_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(MCP_SERVERS)  # ty: ignore[invalid-argument-type]  # upstream typing


async def load_media_tools() -> tuple[list[BaseTool], MultiServerMCPClient]:
    client = create_media_mcp_client()
    tools = await client.get_tools()
    logger.info(f"Loaded {len(tools)} MCP media tools")
    return tools, client
