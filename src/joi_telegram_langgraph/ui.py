import telegramify_markdown
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from joi_langgraph_client.client import format_tool_status
from joi_langgraph_client.types import InterruptData, TokenUsage, ToolState
from joi_telegram_langgraph.app import DEBUG_STATS

TELEGRAM_MSG_LIMIT = 4096


class ConfirmCallback(CallbackData, prefix="cfm"):
    thread_id: str
    approved: bool


def _chunk_text(text: str, limit: int = TELEGRAM_MSG_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to split on paragraph boundary
        cut = text.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks


async def send_markdown(message: Message, text: str, keyboard=None) -> Message | None:
    if not text:
        return None
    converted = telegramify_markdown.markdownify(text)
    chunks = _chunk_text(converted)
    sent: Message | None = None
    for i, chunk in enumerate(chunks):
        kb = keyboard if i == len(chunks) - 1 else None
        try:
            sent = await message.answer(chunk, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}\nConverted: {chunk!r}")
            # Fallback: send original text chunk (un-markdownified)
            original_chunks = _chunk_text(text)
            idx = min(i, len(original_chunks) - 1)
            sent = await message.answer(original_chunks[idx], reply_markup=kb)
    return sent


class TelegramRenderer:
    def __init__(self, message: Message):
        self._message = message
        self._status_message: Message | None = None
        self._last_reply: Message | None = None
        self._last_reply_text: str = ""

    async def send_text(self, text: str) -> None:
        self._last_reply = await send_markdown(self._message, text)
        self._last_reply_text = text

    async def update_status(self, text: str) -> None:
        try:
            if self._status_message:
                await self._status_message.edit_text(text)
            else:
                self._status_message = await self._message.answer(text)
        except Exception as e:
            logger.warning(f"Status update failed: {e}")

    async def show_error(self, error: str) -> None:
        await self.update_status(f"Error: {error}")

    async def show_completion(self, tools: list[ToolState], usage: TokenUsage) -> None:
        if DEBUG_STATS and self._last_reply:
            footer = _format_debug(tools, usage)
            if footer:
                combined = self._last_reply_text + "\n\n" + footer
                await _edit_markdown(self._last_reply, combined)
            if self._status_message:
                try:
                    await self._status_message.delete()
                except Exception:
                    pass
                self._status_message = None
            return

        parts = []
        if tools:
            parts.append(format_tool_status(tools))
        if usage.total > 0:
            parts.append(usage.format())
        if parts:
            await self.update_status(" | ".join(parts))
        elif self._status_message:
            try:
                await self._status_message.delete()
            except Exception as e:
                logger.warning(f"Failed to delete status message: {e}")
            self._status_message = None


def _format_debug(tools: list[ToolState], usage: TokenUsage) -> str:
    parts: list[str] = []
    if tools:
        names = [t.name for t in tools]
        parts.append("tools: " + " → ".join(names))
    if usage.total > 0:
        parts.append(usage.format_debug())
    if not parts:
        return ""
    return "---\n" + "\n".join(parts)


async def _edit_markdown(msg: Message, text: str) -> None:
    converted = telegramify_markdown.markdownify(text)
    chunks = _chunk_text(converted)
    try:
        await msg.edit_text(chunks[-1], parse_mode=ParseMode.MARKDOWN_V2)
    except Exception:
        try:
            await msg.edit_text(text[-TELEGRAM_MSG_LIMIT:])
        except Exception as e:
            logger.warning(f"Debug edit failed: {e}")


def build_confirm_keyboard(thread_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Yes",
                    callback_data=ConfirmCallback(thread_id=thread_id, approved=True).pack(),
                ),
                InlineKeyboardButton(
                    text="No",
                    callback_data=ConfirmCallback(thread_id=thread_id, approved=False).pack(),
                ),
            ]
        ]
    )


def format_interrupt(interrupt: InterruptData) -> str:
    return interrupt.format_text()
