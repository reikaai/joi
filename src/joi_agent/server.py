import os
from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from agno.os import AgentOS
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, Field

load_dotenv()

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logger.add(LOGS_DIR / "joi_agent.log", rotation="10 MB", retention="7 days")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
db = SqliteDb(db_file=str(DATA_DIR / "joi.db"))

PERSONA_PATH = Path(__file__).parent / "persona.md"
MCP_TMDB_URL = "http://127.0.0.1:8000/tmdb"
MCP_TRANSMISSION_URL = "http://127.0.0.1:8000/transmission"


class AgentResponse(BaseModel):
    content: str = Field(description="The response text to show the user")
    suggested_actions: list[str] = Field(
        description="Exactly 3 ultra-brief dialog options (1-3 words). Mix responses and questions. Casual, lowercase.",
        min_length=3,
        max_length=3,
    )


tmdb_tools = MCPTools(url=MCP_TMDB_URL, transport="streamable-http")
transmission_tools = MCPTools(url=MCP_TRANSMISSION_URL, transport="streamable-http")

joi = Agent(
    id="joi",
    name="Joi",
    model=OpenRouter(id="openai/gpt-4o-mini"),
    tools=[tmdb_tools, transmission_tools],
    instructions=PERSONA_PATH.read_text(),
    markdown=True,
    output_schema=AgentResponse,
    db=db,
    enable_user_memories=True,
    enable_agentic_memory=True,
    enable_session_summaries=True,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    learning=True,
    debug_mode=os.getenv("AGNO_DEBUG", "").lower() == "true",
)

agent_os = AgentOS(
    name="Joi OS",
    description="Joi AI assistant",
    agents=[joi],
    tracing=True,
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="joi_agent.server:app", port=7777)
