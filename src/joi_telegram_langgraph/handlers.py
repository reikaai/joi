import asyncio
from contextlib import asynccontextmanager

from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from joi_agent_langgraph2.tasks.models import TaskStatus
from joi_langgraph_client.client import AgentStreamClient
from joi_langgraph_client.session import ApprovalGate, MessageDebouncer, make_thread_id, periodic_callback
from joi_langgraph_client.types import InterruptData

from .app import bot, langgraph, router, settings, task_client
from .ui import ConfirmCallback, TelegramRenderer, build_confirm_keyboard, format_interrupt, send_markdown

_approver = ApprovalGate()
_debouncer = MessageDebouncer(timeout=0.5)


@asynccontextmanager
async def _typing_indicator(chat_id: int):
    async with periodic_callback(lambda: bot.send_chat_action(chat_id, ChatAction.TYPING)):
        yield


async def _run_session(content: str, user_id: str, chat_id: int, message: Message) -> None:
    thread_id = make_thread_id("tg", user_id)

    async with _typing_indicator(chat_id):
        renderer = TelegramRenderer(message)
        client = AgentStreamClient(thread_id, renderer, langgraph, settings.assistant_id, user_id=user_id)

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
            logger.error(f"[user:{user_id}] stream timeout")
            await message.answer("Request timed out, please try again.")
        except Exception as e:
            logger.exception(f"[user:{user_id}] agent error: {e}")
            await message.answer("Sorry, something went wrong.")


async def _try_task_reply(message: Message, user_id: str) -> bool:
    reply = message.reply_to_message
    if not reply:
        return False

    reply_msg_id = reply.message_id
    try:
        tasks = await task_client.list_tasks(user_id, statuses={TaskStatus.WAITING_USER})
    except Exception as e:
        logger.warning(f"Task reply check failed: {e}")
        return False

    for task in tasks:
        if task.question_msg_id == reply_msg_id:
            answer = message.text or ""
            task.status = TaskStatus.RUNNING
            task.question = None
            task.question_msg_id = None
            task.notified = False
            task.append_log("answered", answer)
            await task_client.put_task(task)
            msg = f"[User answered your question]\n\n{answer}\n\nContinue the task with this information."
            await task_client.resume_run(
                task.thread_id,
                input={"messages": [{"role": "user", "content": msg}]},
                config={"configurable": {"user_id": user_id}},
            )
            await message.answer("Got it, resuming the task...")
            logger.info(f"[user:{user_id}] task reply routed: task={task.task_id}")
            return True

    return False


async def _try_task_interrupt_resolve(callback_data: ConfirmCallback) -> bool:
    if not callback_data.task_id:
        return False

    task = await task_client.get_task(callback_data.user_id, callback_data.task_id)
    if not task or task.interrupt_data is None:
        return False

    interrupt = InterruptData.from_stream([task.interrupt_data])
    resume_value = interrupt.build_resume_value(callback_data.approved)

    try:
        await task_client.resume_interrupt(
            task.thread_id,
            command={"resume": resume_value},
            config={"configurable": {"user_id": task.user_id}},
        )
        task.interrupt_data = None
        task.interrupt_msg_id = None
        task.append_log("interrupt_resolved", "approved" if callback_data.approved else "rejected")
        await task_client.put_task(task)
        logger.info(f"Task interrupt resolved: task={task.task_id} approved={callback_data.approved}")
        return True
    except Exception as e:
        logger.error(f"Failed to resume task interrupt: {e}")
        return False


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
    resolved = await _try_task_interrupt_resolve(callback_data)
    if not resolved:
        _approver.resolve(callback_data.thread_id, callback_data.approved)
    label = "Approved" if callback_data.approved else "Rejected"
    await callback.answer(label)
    if callback.message and resolved:
        try:
            await callback.message.edit_text(f"{callback.message.text}\n\n{label}")
        except Exception:
            pass


@router.message()
async def handle(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    user_id = str(message.from_user.id)
    logger.info(f"[user:{user_id}] input: {message.text!r}")

    if await _try_task_reply(message, user_id):
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async def on_debounce(combined: str, msg: Message):
        logger.info(f"[user:{user_id}] debounced input: {combined!r}")
        await _run_session(combined, user_id, msg.chat.id, msg)

    await _debouncer.add(user_id, message.text, message, on_debounce)
