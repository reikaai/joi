from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware, SummarizationMiddleware
from langchain_core.messages.utils import trim_messages
from langchain_openai import ChatOpenAI
from langgraph_swarm import create_handoff_tool, create_swarm
from langmem import create_manage_memory_tool, create_search_memory_tool
from loguru import logger

from joi_agent_langgraph.config import (
    LLM_MODEL,
    LOGS_DIR,
    MEDIA_PERSONA_PATH,
    OPENROUTER_API_KEY,
    PERSONA_PATH,
)
from joi_agent_langgraph.tools import load_media_tools

logger.add(LOGS_DIR / "joi_agent_langgraph.log", rotation="10 MB", retention="7 days")

MUTATION_TOOLS = {
    "add_torrent",
    "remove_torrent",
    "pause_torrent",
    "resume_torrent",
    "set_file_priorities",
}


def _agent_complete(state):
    last_msg = state["messages"][-1]
    agent_name = state.get("active_agent", "agent")
    modified = last_msg.model_copy(update={"content": f"{last_msg.content}\n\n[{agent_name} work completed]"})
    return {"active_agent": "joi", "messages": [modified]}


def get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL.replace("openai/", ""),
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


class TrimToolHeavyHistory(AgentMiddleware):
    """Non-destructive trim: caps tokens sent to model without modifying state."""

    def _trim(self, messages):
        return trim_messages(
            messages,
            max_tokens=8000,
            token_counter="approximate",
            strategy="last",
            start_on="human",
            allow_partial=False,
        )

    def wrap_model_call(self, request, handler):
        return handler(request.override(messages=self._trim(request.messages)))

    async def awrap_model_call(self, request, handler):
        return await handler(request.override(messages=self._trim(request.messages)))


MEMORY_NS = ("{thread_id}", "memories")


class _GraphFactory:
    """Async context manager — lazily builds the swarm graph on first access."""

    def __init__(self):
        self._graph = None
        self._mcp_client = None

    async def __aenter__(self):
        if self._graph is not None:
            return self._graph

        media_tools, self._mcp_client = await load_media_tools()
        media_persona = MEDIA_PERSONA_PATH.read_text() if MEDIA_PERSONA_PATH.exists() else ""

        summarization = SummarizationMiddleware(
            model=get_model(),
            trigger=[("tokens", 4000), ("messages", 10)],
            keep=("messages", 6),
        )

        hitl = HumanInTheLoopMiddleware(
            interrupt_on={name: {"allowed_decisions": ["approve", "reject"]} for name in MUTATION_TOOLS},
        )

        media_agent = create_agent(
            model=get_model(),
            tools=media_tools,
            system_prompt=media_persona,
            name="media_manager",
            middleware=[summarization, TrimToolHeavyHistory(), hitl],
        )

        joi_persona = PERSONA_PATH.read_text() if PERSONA_PATH.exists() else ""
        joi_agent = create_agent(
            model=get_model(),
            tools=[
                create_handoff_tool(
                    agent_name="media_manager",
                    description="Delegate media tasks (search/download/manage movies, torrents, shows) to the Media Manager specialist.",
                ),
                create_manage_memory_tool(namespace=MEMORY_NS),
                create_search_memory_tool(namespace=MEMORY_NS),
            ],
            system_prompt=joi_persona,
            name="joi",
            middleware=[summarization],
        )

        workflow = create_swarm(
            [joi_agent, media_agent],
            default_active_agent="joi",
        )
        workflow.add_node("_agent_done", _agent_complete)
        workflow.add_edge("media_manager", "_agent_done")
        workflow.add_edge("_agent_done", "joi")
        self._graph = workflow.compile()
        logger.info("Swarm graph compiled")
        return self._graph

    async def __aexit__(self, *args):
        pass


_factory = _GraphFactory()


def graph():
    return _factory
