import asyncio
import os
import signal
import uuid
from pathlib import Path

import telegramify_markdown
from agno.client import AgentOSClient
from agno.run.agent import IntermediateRunContentEvent, RunContentEvent
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

load_dotenv()

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logger.add(LOGS_DIR / "joi_telegram.log", rotation="10 MB", retention="7 days")

AGENTOS_URL = os.getenv("AGENTOS_URL", "http://localhost:7777")
OS_SECURITY_KEY = os.getenv("OS_SECURITY_KEY")
AUTH_HEADERS = {"Authorization": f"Bearer {OS_SECURITY_KEY}"} if OS_SECURITY_KEY else None


class ActionCallback(CallbackData, prefix="act"):
    action_id: str


action_cache: dict[str, str] = {}


def store_action(text: str) -> str:
    action_id = uuid.uuid4().hex[:8]
    action_cache[action_id] = text
    return action_id


def build_actions_keyboard(actions: list[str]):
    builder = InlineKeyboardBuilder()
    for action in actions:
        action_id = store_action(action)
        builder.button(text=action[:40], callback_data=ActionCallback(action_id=action_id).pack())
    builder.adjust(1)
    return builder.as_markup()


bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
router = Router()
dp = Dispatcher()
dp.include_router(router)

client = AgentOSClient(base_url=AGENTOS_URL)


class AgentResponse(BaseModel):
    content: str
    suggested_actions: list[str] = []


@router.message(CommandStart())
async def start(message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ask a question", callback_data="ask")]])
    await message.answer("Ready. Ask me anything or tap below.", reply_markup=kb)


@router.callback_query(lambda c: c.data == "ask")
async def on_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Type your question:")


async def run_agent(content: str, user_id: str, chat_id: int, message: Message) -> None:
    """Stream agent responses, sending each to Telegram immediately."""

    async def keep_typing():
        while True:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)

    typing_task = asyncio.create_task(keep_typing())

    async def send_response(response: AgentResponse) -> None:
        if not response.content:
            return
        keyboard = build_actions_keyboard(response.suggested_actions) if response.suggested_actions else None
        converted = telegramify_markdown.markdownify(response.content)
        try:
            await message.answer(converted, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}\nOriginal: {response.content!r}\nConverted: {converted!r}")
            await message.answer(response.content, reply_markup=keyboard)

    try:
        stream = client.run_agent_stream(
            agent_id="joi",
            message=content,
            user_id=user_id,
            session_id=user_id,
            headers=AUTH_HEADERS,
        )

        event_count = 0
        async for event in stream:
            logger.debug(f"Stream event: {type(event).__name__}")
            match event:
                case RunContentEvent(content=c) if c:
                    event_count += 1
                    logger.info(f"RunContentEvent #{event_count}, content_type={type(c).__name__}")
                    response = AgentResponse.model_validate_json(c) if isinstance(c, str) else AgentResponse.model_validate(c)
                    await send_response(response)
                case IntermediateRunContentEvent():
                    pass  # Skip partial content
                case _:
                    pass
        logger.info(f"Stream completed with {event_count} RunContentEvent(s)")
    except Exception as e:
        logger.exception(f"Agent stream error: {e}")
        await message.answer("Sorry, something went wrong.")
    finally:
        typing_task.cancel()


@router.callback_query(ActionCallback.filter())
async def on_action(callback: CallbackQuery, callback_data: ActionCallback) -> None:
    action_text = action_cache.get(callback_data.action_id)
    if not action_text:
        await callback.answer("Action expired")
        return
    if not callback.message or not callback.from_user:
        return
    if not isinstance(callback.message, Message):
        return

    await callback.answer()
    await callback.message.answer(f"➡️ {action_text}")
    await run_agent(action_text, str(callback.from_user.id), callback.message.chat.id, callback.message)


@router.message()
async def handle(message: Message) -> None:
    if not message.from_user:
        return
    content = message.text
    if not content:
        return
    await run_agent(content, str(message.from_user.id), message.chat.id, message)


async def main() -> None:
    logger.info(f"Starting Joi Telegram bot... AGENTOS_URL={AGENTOS_URL}")

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
