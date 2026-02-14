import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from loguru import logger
from mem0 import Memory

from joi_agent_langgraph2.config import MEM0_CONFIG

_mem0: Memory | None = None


def get_mem0() -> Memory:
    global _mem0
    if _mem0 is None:
        _mem0 = Memory.from_config(MEM0_CONFIG)
        logger.info("Mem0 initialized")
    return _mem0


@tool
async def remember(fact: str, config: RunnableConfig) -> str:
    """Remember a fact or preference for the user. Use this to store information the user wants you to remember."""
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    mem0 = get_mem0()
    await asyncio.to_thread(mem0.add, fact, user_id=thread_id)
    logger.info(f"Remembered fact for thread {thread_id}: {fact[:80]}")
    return f"Remembered: {fact}"


@tool
async def recall(query: str, config: RunnableConfig) -> str:
    """Recall memories relevant to a query. Use this to retrieve previously stored information about the user."""
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    mem0 = get_mem0()
    results = await asyncio.to_thread(mem0.search, query, user_id=thread_id)
    if not results or not results.get("results"):
        return "No relevant memories found."
    memories = [r["memory"] for r in results["results"]]
    formatted = "\n".join(f"- {m}" for m in memories)
    logger.info(f"Recalled {len(memories)} memories for thread {thread_id}")
    return f"Relevant memories:\n{formatted}"
