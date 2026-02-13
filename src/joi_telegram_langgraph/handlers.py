import asyncio
import uuid

from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from .app import ASSISTANT_ID, bot, langgraph, router
from .stream import _handle_stream


class ActionCallback(CallbackData, prefix="act"):
    action_id: str


class ConfirmCallback(CallbackData, prefix="cfm"):
    thread_id: str
    approved: bool


action_cache: dict[str, str] = {}
pending_confirms: dict[str, dict] = {}
_debounce: dict[str, tuple[asyncio.Task, list[str], Message]] = {}
DEBOUNCE_SECONDS = 1.5


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


@router.message(CommandStart())
async def start(message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ask a question", callback_data="ask")]])
    await message.answer("Ready (LangGraph). Ask me anything or tap below.", reply_markup=kb)


@router.callback_query(lambda c: c.data == "ask")
async def on_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Type your question:")


async def run_agent(content: str, user_id: str, chat_id: int, message: Message) -> None:
    async def keep_typing():
        while True:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)

    typing_task = asyncio.create_task(keep_typing())
    tool_states: list[tuple[str, str]] = []
    status_message: Message | None = None

    async def update_status(text: str) -> None:
        nonlocal status_message
        try:
            if status_message:
                await status_message.edit_text(text)
            else:
                status_message = await message.answer(text)
        except Exception as e:
            logger.warning(f"Status update failed: {e}")

    thread_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tg-{user_id}"))

    try:
        await update_status("Processing...")

        stream = langgraph.runs.stream(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            input={"messages": [{"role": "user", "content": content}]},
            stream_mode=["updates", "messages-tuple", "custom"],
            if_not_exists="create",
            stream_subgraphs=True,
        )
        await asyncio.wait_for(
            _handle_stream(
                stream,
                thread_id,
                message,
                tool_states,
                update_status,
                pending_confirms,
                resume_agent,
                ConfirmCallback,
            ),
            timeout=600,
        )

    except TimeoutError:
        logger.error(f"Stream timeout for user {user_id}")
        await message.answer("Request timed out, please try again.")
    except Exception as e:
        logger.exception(f"Agent stream error: {e}")
        await message.answer("Sorry, something went wrong.")
    finally:
        typing_task.cancel()


async def resume_agent(thread_id: str, approved: bool, message: Message, tool_states: list, update_status) -> None:
    try:
        confirm_data = pending_confirms.pop(thread_id, {})
        action_count = confirm_data.get("action_count", 1)
        interrupt_id = confirm_data.get("interrupt_id")

        decision = {"type": "approve"} if approved else {"type": "reject"}
        hitl_response = {"decisions": [decision] * action_count}

        resume_value = hitl_response
        if interrupt_id:
            resume_value = {interrupt_id: hitl_response}

        stream = langgraph.runs.stream(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            command={"resume": resume_value},
            stream_mode=["updates", "messages-tuple", "custom"],
            stream_subgraphs=True,
        )
        await asyncio.wait_for(
            _handle_stream(
                stream,
                thread_id,
                message,
                tool_states,
                update_status,
                pending_confirms,
                resume_agent,
                ConfirmCallback,
            ),
            timeout=600,
        )

    except TimeoutError:
        logger.error(f"Resume stream timeout for thread {thread_id}")
        await message.answer("Request timed out, please try again.")
    except Exception as e:
        logger.exception(f"Resume error: {e}")
        await message.answer("Resume failed.")


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
    await callback.message.answer(f"-> {action_text}")
    await run_agent(action_text, str(callback.from_user.id), callback.message.chat.id, callback.message)


@router.callback_query(ConfirmCallback.filter())
async def on_confirm(callback: CallbackQuery, callback_data: ConfirmCallback) -> None:
    data = pending_confirms.get(callback_data.thread_id)
    if not data:
        await callback.answer("Expired")
        return

    data["approved"] = callback_data.approved
    data["event"].set()
    await callback.answer("yes" if callback_data.approved else "no")


@router.message()
async def handle(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    user_id = str(message.from_user.id)
    content = message.text

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if user_id in _debounce:
        task, messages, _ = _debounce[user_id]
        task.cancel()
        messages.append(content)
    else:
        messages = [content]

    async def fire():
        await asyncio.sleep(DEBOUNCE_SECONDS)
        data = _debounce.pop(user_id, None)
        if data:
            _, msgs, msg = data
            combined = "\n".join(msgs)
            await run_agent(combined, user_id, msg.chat.id, msg)

    _debounce[user_id] = (asyncio.create_task(fire()), messages, message)
