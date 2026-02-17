from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langsmith import traceable

from joi_agent_langgraph2.tools import MUTATION_TOOLS


def create_media_delegate(
    model: BaseChatModel, media_tools: list[BaseTool], media_persona: str, interpreter: BaseTool | None = None,
) -> BaseTool:
    tools = list(media_tools)
    if interpreter:
        tools.append(interpreter)

    media_agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=media_persona,
        name="media_manager",
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={name: {"allowed_decisions": ["approve", "reject"]} for name in MUTATION_TOOLS},
            ),
        ],
    )

    @tool
    @traceable(name="media-delegate")
    async def delegate_media(query: str) -> str:
        """Query or manage media: what's downloaded, active torrents, search/download movies/shows.

        Use for ANY question about movies, shows, or torrents.
        """
        result = await media_agent.ainvoke({"messages": [HumanMessage(content=query)]})
        return result["messages"][-1].content

    return delegate_media
