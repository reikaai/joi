import asyncio
from typing import Any, NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, before_agent, wrap_model_call
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph_sdk import get_client as get_langgraph
from loguru import logger
from mem0 import Memory

from joi_agent_langgraph2.calendar.tools import create_calendar_tools
from joi_agent_langgraph2.config import settings
from joi_agent_langgraph2.delegates import create_media_delegate
from joi_agent_langgraph2.interpreter import create_interpreter_tool
from joi_agent_langgraph2.memory import create_memory_tools
from joi_agent_langgraph2.tasks.tools import create_task_tools
from joi_agent_langgraph2.tools import load_media_tools, prepare_tools
from joi_agent_langgraph2.transcribe import create_transcribe_tool


@tool
async def think(thought: str) -> str:
    """Use to reason step by step before acting. No side effects — just structured thinking space.
    Use when: processing complex tool results, deciding between options, checking if you have all info needed."""
    return "OK"


logger.add(settings.logs_dir / "joi_agent_langgraph2.log", rotation="10 MB", retention="7 days")

SUMMARIZE_AFTER = 80
KEEP_LAST = 40
KEEP_TOOL_RESULTS = 10


class JoiState(AgentState):
    summary: NotRequired[str]


def get_model() -> ChatAnthropic:
    return ChatAnthropic(  # ty: ignore[missing-argument]  # model is alias for model_name
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        stream_usage=True,
    )


@before_agent(state_schema=JoiState)  # ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244
async def summarize_if_needed(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
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


@wrap_model_call(state_schema=JoiState)  # ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244
async def inject_summary(request: Any, handler: Any) -> Any:
    summary = request.state.get("summary", "")
    if summary:
        existing = request.system_message
        prefix = f"{existing.content}\n\n" if existing else ""
        new_sys = SystemMessage(content=f"{prefix}<conversation_summary>\n{summary}\n</conversation_summary>")
        request = request.override(system_message=new_sys)
    return await handler(request)


def truncate_tool_results(messages: list, keep: int = KEEP_TOOL_RESULTS) -> list:
    result = list(messages)
    tool_count = 0
    for i in range(len(result) - 1, -1, -1):
        if isinstance(result[i], ToolMessage):
            tool_count += 1
            if tool_count > keep:
                result[i] = ToolMessage(
                    content="[Output truncated]",
                    tool_call_id=result[i].tool_call_id,
                    id=result[i].id,
                    status=result[i].status,
                )
    return result


@wrap_model_call(state_schema=JoiState)  # ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244
async def truncate_excess_tool_results(request: Any, handler: Any) -> Any:
    masked = truncate_tool_results(request.messages, KEEP_TOOL_RESULTS)
    return await handler(request.override(messages=masked))


ANTHROPIC_CACHE_CONTROL = {"type": "ephemeral", "ttl": "5m"}


@wrap_model_call(state_schema=JoiState)  # ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244
async def anthropic_cache_system_prompt(request: Any, handler: Any) -> Any:
    """Anthropic-specific: mark system prompt as cacheable (prefix breakpoint)."""
    sys_msg = request.system_message
    if sys_msg:
        text = sys_msg.content if isinstance(sys_msg.content, str) else str(sys_msg.content)
        request = request.override(
            system_message=SystemMessage(content=[{"type": "text", "text": text, "cache_control": ANTHROPIC_CACHE_CONTROL}])
        )
    return await handler(request)


class _GraphFactory:
    def __init__(self):
        self._graph = None
        self._mcp_client = None

    async def __aenter__(self):
        if self._graph is not None:
            return self._graph

        # Construction-time DI: initialize all deps
        langgraph = get_langgraph()  # ASGI in-process, no HTTP hop
        mem0 = await asyncio.to_thread(Memory.from_config, settings.mem0_config)

        task_tools = create_task_tools(langgraph, settings.assistant_id)
        calendar_tools = create_calendar_tools()
        memory_tools = create_memory_tools(mem0)

        media_tools, self._mcp_client = await load_media_tools()
        media_persona = settings.media_persona_path.read_text() if settings.media_persona_path.exists() else ""
        joi_persona = settings.persona_path.read_text() if settings.persona_path.exists() else ""

        media_interpreter = create_interpreter_tool(
            media_tools,
            name="run_media_code",
            description="Execute Python in a sandbox. All MCP tools available as functions (same names/args). "
            "Also has pathlib and json. Use for chaining lookups, filtering, comparisons. "
            "Do NOT call mutation tools here (add_torrent, remove_torrent, etc.) — they bypass user confirmation. "
            "Last expression is the return value.",
        )
        delegate_media = create_media_delegate(get_model(), media_tools, media_persona, media_interpreter)
        main_interpreter = create_interpreter_tool(
            memory_tools,
            name="run_code",
            description="Execute Python in a sandbox. Available functions: remember(), recall(). "
            "Also has pathlib (persistent home dir) and json. "
            "Use when chaining multiple memory ops or computing over results. "
            "Last expression is the return value.",
        )

        transcribe_tool = create_transcribe_tool()

        self._graph = create_agent(
            model=get_model(),
            tools=prepare_tools([
                delegate_media,
                *memory_tools,
                think,
                main_interpreter,
                *task_tools,
                *calendar_tools,
                transcribe_tool,
                # Anthropic native server-side tools (no client execution needed)
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
                {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 3, "citations": {"enabled": True}},
            ]),
            system_prompt=joi_persona,
            # name removed: LangGraph sets AIMessage.name from this param, which leaks into
            # OpenAI API history as {"role":"assistant","name":"joi_v2",...} — the LLM then
            # mimics the pattern and prefixes its content with "joi_v2:". Only needed for
            # multi-agent orchestration, not applicable here.
            state_schema=JoiState,
            middleware=[  # ty: ignore[invalid-argument-type]  # upstream: langchain-ai/langchain#35244
                summarize_if_needed,
                truncate_excess_tool_results,
                inject_summary,
                anthropic_cache_system_prompt,
                AnthropicPromptCachingMiddleware(),
            ],
        )
        logger.info("joi agent compiled")
        return self._graph

    async def __aexit__(self, *args):
        pass


_factory = _GraphFactory()


def graph():
    return _factory
