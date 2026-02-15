import asyncio
import signal

from loguru import logger

from . import handlers  # noqa: F401
from .app import bot, dp, settings


async def main() -> None:
    logger.info(f"Starting Joi Telegram (LangGraph)... LANGGRAPH_URL={settings.langgraph_url}")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    polling_task = asyncio.create_task(dp.start_polling(bot))

    await stop_event.wait()
    logger.info("Stopping polling...")

    await dp.stop_polling()
    await bot.session.close()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
