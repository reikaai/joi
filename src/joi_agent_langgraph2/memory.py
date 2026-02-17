import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from loguru import logger
from mem0 import Memory


def create_memory_tools(mem0: Memory) -> list[BaseTool]:
    @tool
    async def remember(fact: str, config: RunnableConfig) -> str:
        """Remember a fact or preference for the user. Use this to store information the user wants you to remember."""
        cfg = config.get("configurable", {})
        uid = cfg.get("user_id") or cfg.get("thread_id") or "default"
        await asyncio.to_thread(mem0.add, fact, user_id=uid)
        logger.info(f"Remembered fact for user {uid}: {fact[:80]}")
        return f"Remembered: {fact}"

    @tool
    async def recall(query: str, config: RunnableConfig) -> str:
        """Recall personal facts/preferences previously saved about the user.

        NOT for media, downloads, or torrents — use delegate_media for those.
        """
        cfg = config.get("configurable", {})
        uid = cfg.get("user_id") or cfg.get("thread_id") or "default"
        results = await asyncio.to_thread(mem0.search, query, user_id=uid)
        if not results or not results.get("results"):
            return "No relevant memories found."
        memories = [r["memory"] for r in results["results"]]
        formatted = "\n".join(f"- {m}" for m in memories)
        logger.info(f"Recalled {len(memories)} memories for user {uid}")
        return f"Relevant memories:\n{formatted}"

    return [remember, recall]
