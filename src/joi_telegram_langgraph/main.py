import asyncio

from aiogram import Bot
from loguru import logger

from . import handlers  # noqa: F401
from .app import bot, dp, settings, task_client
from .notifier import run_notifier

_background_tasks: set[asyncio.Task] = set()


@dp.startup()
async def on_startup(bot: Bot, **_kw) -> None:
    logger.info(f"Starting Joi Telegram (LangGraph)... LANGGRAPH_URL={settings.langgraph_url}")
    task = asyncio.create_task(run_notifier(bot, task_client, debug=settings.task_debug))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@dp.shutdown()
async def on_shutdown(bot: Bot, **_kw) -> None:
    logger.info("Shutting down...")
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    logger.info("Bot shutdown complete")


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
