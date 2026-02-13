import asyncio

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

from joi_agent_langgraph.config import MCP_BASE_URL, PLAYWRIGHT_MCP_URL

MCP_SERVERS = {
    "tmdb": {
        "url": f"{MCP_BASE_URL}/tmdb/",
        "transport": "streamable_http",
    },
    "transmission": {
        "url": f"{MCP_BASE_URL}/transmission/",
        "transport": "streamable_http",
    },
    "jackett": {
        "url": f"{MCP_BASE_URL}/jackett/",
        "transport": "streamable_http",
    },
}

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 1.0


def _wrap_with_progress(tool: BaseTool) -> BaseTool:
    original_coro = tool.coroutine  # type: ignore[union-attr]

    async def _wrapped(**kwargs):
        from langgraph.config import get_stream_writer

        try:
            writer = get_stream_writer()
        except Exception:
            writer = None

        args_str = ", ".join(f"{v}" for v in kwargs.values())
        display = f"{tool.name}({args_str})" if args_str else tool.name

        if writer:
            writer({"type": "tool_start", "tool": tool.name, "display": display})

        last_err: Exception | None = None
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                result = await original_coro(**kwargs)
                if writer:
                    writer({"type": "tool_done", "tool": tool.name})
                return result
            except Exception as e:
                last_err = e
                if attempt < MAX_RETRY_ATTEMPTS:
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


PLAYWRIGHT_MCP_SERVERS = {
    "playwright": {
        "url": f"{PLAYWRIGHT_MCP_URL}/mcp",
        "transport": "streamable_http",
    },
}


def create_playwright_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(PLAYWRIGHT_MCP_SERVERS)


async def load_playwright_tools() -> tuple[list[BaseTool], MultiServerMCPClient]:
    client = create_playwright_mcp_client()
    tools = await client.get_tools()
    tools = [_wrap_with_progress(t) for t in tools]
    logger.info(f"Loaded {len(tools)} playwright tools (with progress + retry)")
    return tools, client


def create_media_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(MCP_SERVERS)


async def load_media_tools() -> tuple[list[BaseTool], MultiServerMCPClient]:
    client = create_media_mcp_client()
    tools = await client.get_tools()
    tools = [_wrap_with_progress(t) for t in tools]
    logger.info(f"Loaded {len(tools)} MCP media tools (with progress + retry)")
    return tools, client
