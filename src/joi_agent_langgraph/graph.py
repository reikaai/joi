from typing import NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentState,
    HumanInTheLoopMiddleware,
    before_agent,
    wrap_model_call,
)
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph_swarm import SwarmState, create_handoff_tool, create_swarm
from langmem import create_manage_memory_tool, create_search_memory_tool
from loguru import logger

from joi_agent_langgraph.config import (
    LLM_MODEL,
    LOGS_DIR,
    MEDIA_PERSONA_PATH,
    OPENROUTER_API_KEY,
    PERSONA_PATH,
)
from joi_agent_langgraph.tools import load_media_tools, load_playwright_tools

logger.add(LOGS_DIR / "joi_agent_langgraph.log", rotation="10 MB", retention="7 days")

MUTATION_TOOLS = {
    "add_torrent",
    "remove_torrent",
    "pause_torrent",
    "resume_torrent",
    "set_file_priorities",
}

SUMMARIZE_AFTER = 10
KEEP_LAST = 6


class JoiSwarmState(SwarmState):
    summary: NotRequired[str]


class SummaryAgentState(AgentState):
    summary: NotRequired[str]


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
        stream_usage=True,
    )


@before_agent(state_schema=SummaryAgentState)
async def summarize_if_needed(state, runtime):
    messages = state["messages"]
    if len(messages) <= SUMMARIZE_AFTER:
        return None

    to_summarize = messages[:-KEEP_LAST]

    existing = state.get("summary", "")
    prompt_text = (
        f"Existing summary:\n{existing}\n\nExtend with the new messages above:"
        if existing
        else "Create a brief summary of the conversation above:"
    )

    resp = await get_model().ainvoke([*to_summarize, HumanMessage(content=prompt_text)])

    usage = getattr(resp, "usage_metadata", None)
    logger.info(f"Summarized {len(to_summarize)} messages → {len(resp.content)} chars" + (f" | tokens: {usage}" if usage else ""))

    delete = [RemoveMessage(id=m.id) for m in to_summarize if hasattr(m, "id") and m.id]
    return {"summary": resp.content, "messages": delete}


@wrap_model_call(state_schema=SummaryAgentState)
async def inject_summary(request, handler):
    summary = request.state.get("summary", "")
    if summary:
        existing = request.system_message
        prefix = f"{existing.content}\n\n" if existing else ""
        new_sys = SystemMessage(content=f"{prefix}<conversation_summary>\n{summary}\n</conversation_summary>")
        request = request.override(system_message=new_sys)
    return await handler(request)


MEMORY_NS = ("{thread_id}", "memories")


class _GraphFactory:
    def __init__(self):
        self._graph = None
        self._mcp_client = None
        self._playwright_client = None

    async def __aenter__(self):
        if self._graph is not None:
            return self._graph

        media_tools, self._mcp_client = await load_media_tools()
        browser_tools, self._playwright_client = await load_playwright_tools()
        media_persona = MEDIA_PERSONA_PATH.read_text() if MEDIA_PERSONA_PATH.exists() else ""

        hitl = HumanInTheLoopMiddleware(
            interrupt_on={name: {"allowed_decisions": ["approve", "reject"]} for name in MUTATION_TOOLS},
        )

        media_agent = create_agent(
            model=get_model(),
            tools=media_tools,
            system_prompt=media_persona,
            name="media_manager",
            middleware=[inject_summary, hitl],
        )

        browser_agent = create_agent(
            model=get_model(),
            tools=browser_tools,
            system_prompt="You are a web browser agent. Navigate, interact with, and extract information from web pages.",
            name="browser",
            middleware=[inject_summary],
        )

        joi_persona = PERSONA_PATH.read_text() if PERSONA_PATH.exists() else ""
        joi_agent = create_agent(
            model=get_model(),
            tools=[
                create_handoff_tool(
                    agent_name="media_manager",
                    description="Delegate media tasks (search/download/manage movies, torrents, shows) to the Media Manager specialist.",
                ),
                create_handoff_tool(
                    agent_name="browser",
                    description=(
                        "Delegate web browsing tasks (search the web, read pages, fill forms, extract content) to the Browser specialist."
                    ),
                ),
                create_manage_memory_tool(namespace=MEMORY_NS),
                create_search_memory_tool(namespace=MEMORY_NS),
            ],
            system_prompt=joi_persona,
            name="joi",
            middleware=[summarize_if_needed, inject_summary],
        )

        workflow = create_swarm(
            [joi_agent, media_agent, browser_agent],
            default_active_agent="joi",
            state_schema=JoiSwarmState,
        )
        workflow.add_node("_agent_done", _agent_complete)
        workflow.add_edge("media_manager", "_agent_done")
        workflow.add_edge("browser", "_agent_done")
        workflow.add_edge("_agent_done", "joi")
        self._graph = workflow.compile()
        logger.info("Swarm graph compiled")
        return self._graph

    async def __aexit__(self, *args):
        pass


_factory = _GraphFactory()


def graph():
    return _factory
