import os
from pathlib import Path

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv

load_dotenv()

MEDIA_PERSONA_PATH = Path(__file__).parent / "media_persona.md"
MCP_BASE_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000")

tmdb_tools = MCPTools(url=f"{MCP_BASE_URL}/tmdb", transport="streamable-http", tool_name_prefix="tmdb")
transmission_tools = MCPTools(
    url=f"{MCP_BASE_URL}/transmission",
    transport="streamable-http",
    tool_name_prefix="transmission",
    requires_confirmation_tools=["add_torrent", "remove_torrent", "pause_torrent"],
)
jackett_tools = MCPTools(url=f"{MCP_BASE_URL}/jackett", transport="streamable-http", tool_name_prefix="jackett")

media_agent = Agent(
    id="media-manager",
    name="Media Manager",
    role="Handle media download requests: search torrents, manage download queue, select optimal files",
    model=OpenRouter(id=os.getenv("LLM_MODEL", "openai/gpt-4o-mini")),
    tools=[tmdb_tools, transmission_tools, jackett_tools],
    instructions=MEDIA_PERSONA_PATH.read_text(),
    markdown=True,
    add_name_to_context=True,
)
