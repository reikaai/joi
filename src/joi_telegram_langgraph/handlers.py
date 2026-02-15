import asyncio
from contextlib import asynccontextmanager

from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from joi_langgraph_client.client import AgentStreamClient
from joi_langgraph_client.session import ApprovalGate, MessageDebouncer, make_thread_id, periodic_callback

from .app import ASSISTANT_ID, bot, langgraph, router
from .ui import ConfirmCallback, TelegramRenderer, build_confirm_keyboard, format_interrupt, send_markdown

_approver = ApprovalGate()
_debouncer = MessageDebouncer(timeout=1.5)


@asynccontextmanager
async def _typing_indicator(chat_id: int):
    async with periodic_callback(lambda: bot.send_chat_action(chat_id, ChatAction.TYPING)):
        yield


async def _run_session(content: str, user_id: str, chat_id: int, message: Message) -> None:
    thread_id = make_thread_id("tg", user_id)

    async with _typing_indicator(chat_id):
        renderer = TelegramRenderer(message)
        client = AgentStreamClient(thread_id, renderer, langgraph, ASSISTANT_ID)

        try:
            interrupt = await asyncio.wait_for(client.run(content), timeout=600)

            while interrupt:
                text = format_interrupt(interrupt)
                kb = build_confirm_keyboard(thread_id)
                confirm_msg = await message.answer(text, reply_markup=kb)

                approved = await _approver.wait(thread_id, timeout=300)
                await confirm_msg.edit_text("Approved" if approved else "Rejected")

                if not approved:
                    await send_markdown(message, "Action cancelled.")
                    break

                interrupt = await asyncio.wait_for(client.resume(interrupt, approved), timeout=600)

        except TimeoutError:
            logger.error(f"Stream timeout for user {user_id}")
            await message.answer("Request timed out, please try again.")
        except Exception as e:
            logger.exception(f"Agent error: {e}")
            await message.answer("Sorry, something went wrong.")


# --- Handlers ---


@router.message(CommandStart())
async def start(message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ask a question", callback_data="ask")]])
    await message.answer("Ready (LangGraph). Ask me anything or tap below.", reply_markup=kb)


@router.callback_query(lambda c: c.data == "ask")
async def on_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Type your question:")


@router.callback_query(ConfirmCallback.filter())
async def on_confirm(callback: CallbackQuery, callback_data: ConfirmCallback) -> None:
    _approver.resolve(callback_data.thread_id, callback_data.approved)
    await callback.answer("yes" if callback_data.approved else "no")


@router.message()
async def handle(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    user_id = str(message.from_user.id)

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async def on_debounce(combined: str, msg: Message):
        await _run_session(combined, user_id, msg.chat.id, msg)

    await _debouncer.add(user_id, message.text, message, on_debounce)
