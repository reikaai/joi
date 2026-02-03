import os
from pathlib import Path

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.os import AgentOS
from agno.session import SessionSummaryManager
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

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    from agno.db.postgres import PostgresDb
    db = PostgresDb(db_url=DATABASE_URL)
    logger.info("Using PostgreSQL database")
else:
    from agno.db.sqlite import SqliteDb
    db = SqliteDb(db_file=str(DATA_DIR / "joi.db"))
    logger.info("Using SQLite database")

PERSONA_PATH = Path(__file__).parent / "persona.md"
MCP_BASE_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000")
MCP_TMDB_URL = f"{MCP_BASE_URL}/tmdb"
MCP_TRANSMISSION_URL = f"{MCP_BASE_URL}/transmission"

SUMMARY_PROMPT = """Summarize this conversation between user and Joi (AI assistant).

FORMAT - Use shorthand:
- → for causes/leads to
- | for alternatives
- @ for mentions/references
- Keep names, numbers, colors, dates EXACT
- Use emoji sparingly for tone: 😤 annoyed, 🤔 curious, 💬 casual

MUST PRESERVE:
- References to Joi/assistant ("you", "testing you", "experimenting with you") → note Joi is the subject
- Specific facts: colors mentioned, numbers, preferences stated
- Emotional state changes: user mood, Joi's reactions
- Unresolved questions or promises

OUTPUT:
- Summary (str): Condensed bullet points, max 3-5 lines
- Topics (Optional[List[str]]): 2-4 keywords

Example format:
"user testing Joi's memory → asked about blue color | Joi: 🤔 about experiment subject | user frustrated w/ vague answers"

NO fabrication. If uncertain, say "unclear"."""

summary_manager = SessionSummaryManager(
    session_summary_prompt=SUMMARY_PROMPT,
)


class AgentResponse(BaseModel):
    content: str = Field(description="The response text to show the user")
    suggested_actions: list[str] = Field(
        description="Exactly 3 ultra-brief dialog options (1-3 words). Mix responses and questions. Casual, lowercase.",
        min_length=3,
        max_length=3,
    )


tmdb_tools = MCPTools(url=MCP_TMDB_URL, transport="streamable-http", tool_name_prefix="tmdb")
transmission_tools = MCPTools(url=MCP_TRANSMISSION_URL, transport="streamable-http", tool_name_prefix="transmission")

joi = Agent(
    id="joi",
    name="Joi",
    model=OpenRouter(id=os.getenv("LLM_MODEL", "openai/gpt-4o-mini")),
    tools=[tmdb_tools, transmission_tools],
    instructions=PERSONA_PATH.read_text(),
    markdown=True,
    output_schema=AgentResponse,
    db=db,
    enable_user_memories=False,  # Disabled: mutually exclusive with agentic_memory
    enable_agentic_memory=True,  # Agent decides when to save memories via tools
    session_summary_manager=summary_manager,
    enable_session_summaries=True,
    add_session_summary_to_context=True,  # Inject summary into context
    add_history_to_context=True,
    num_history_runs=5,  # TODO: tune later
    max_tool_calls_from_history=2,  # Limit tool result bloat in context
    read_chat_history=True,  # Agent can query full history via get_chat_history()
    add_datetime_to_context=True,
    learning=False,  # Disabled: agentic_memory handles this, avoids 2 extra API calls/msg
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
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "7777"))
    agent_os.serve(app="joi_agent.server:app", host=host, port=port)
