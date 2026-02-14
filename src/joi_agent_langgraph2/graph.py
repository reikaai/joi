from typing import NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, before_agent, wrap_model_call
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from joi_agent_langgraph2.config import (
    LLM_MODEL,
    LOGS_DIR,
    MEDIA_PERSONA_PATH,
    OPENROUTER_API_KEY,
    PERSONA_PATH,
)
from joi_agent_langgraph2.delegates import create_media_delegate
from joi_agent_langgraph2.memory import recall, remember
from joi_agent_langgraph2.tools import load_media_tools

logger.add(LOGS_DIR / "joi_agent_langgraph2.log", rotation="10 MB", retention="7 days")

SUMMARIZE_AFTER = 10
KEEP_LAST = 6


class JoiState(AgentState):
    summary: NotRequired[str]


def get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL.replace("openai/", ""),
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        stream_usage=True,
    )


@before_agent(state_schema=JoiState)
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


@wrap_model_call(state_schema=JoiState)
async def inject_summary(request, handler):
    summary = request.state.get("summary", "")
    if summary:
        existing = request.system_message
        prefix = f"{existing.content}\n\n" if existing else ""
        new_sys = SystemMessage(content=f"{prefix}<conversation_summary>\n{summary}\n</conversation_summary>")
        request = request.override(system_message=new_sys)
    return await handler(request)


class _GraphFactory:
    def __init__(self):
        self._graph = None
        self._mcp_client = None

    async def __aenter__(self):
        if self._graph is not None:
            return self._graph

        media_tools, self._mcp_client = await load_media_tools()
        media_persona = MEDIA_PERSONA_PATH.read_text() if MEDIA_PERSONA_PATH.exists() else ""
        joi_persona = PERSONA_PATH.read_text() if PERSONA_PATH.exists() else ""

        delegate_media = create_media_delegate(get_model(), media_tools, media_persona)

        self._graph = create_agent(
            model=get_model(),
            tools=[delegate_media, remember, recall],
            system_prompt=joi_persona,
            name="joi_v2",
            state_schema=JoiState,
            middleware=[summarize_if_needed, inject_summary],
        )
        logger.info("joi_v2 agent compiled")
        return self._graph

    async def __aexit__(self, *args):
        pass


_factory = _GraphFactory()


def graph():
    return _factory
