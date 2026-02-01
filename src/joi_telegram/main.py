import asyncio
import os
import re
import tempfile
import uuid
from pathlib import Path

import edge_tts
import telegramify_markdown
from agno.client import AgentOSClient
from agno.tools.mlx_transcribe import MLXTranscribeTools
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from loguru import logger
from pydub import AudioSegment

load_dotenv()

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logger.add(LOGS_DIR / "joi_telegram.log", rotation="10 MB", retention="7 days")

AGENTOS_URL = os.getenv("AGENTOS_URL", "http://localhost:7777")
TTS_ENABLED = os.getenv("TTS_ENABLED", "false").lower() == "true"


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
mlx_transcribe = MLXTranscribeTools(restrict_to_base_dir=False)

CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF]")


class TranscriptionError(Exception):
    pass


def detect_language(text: str) -> str:
    cyrillic_count = len(CYRILLIC_PATTERN.findall(text))
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha > 0 and cyrillic_count / total_alpha > 0.3:
        return "ru"
    return "en"


async def text_to_voice(text: str) -> bytes:
    lang = detect_language(text)
    voice = "ru-RU-DmitryNeural" if lang == "ru" else "en-US-GuyNeural"
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = Path(tmpdir) / "voice.mp3"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(mp3_path))
        ogg_path = Path(tmpdir) / "voice.ogg"
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio.export(str(ogg_path), format="ogg", codec="libopus", bitrate="64k")
        return ogg_path.read_bytes()


async def get_message_content(message: Message) -> str | None:
    if message.text:
        return message.text
    if message.voice:
        voice_file = await bot.download(message.voice)
        if voice_file is None:
            return None
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(voice_file.read())
            temp_path = f.name
        result = mlx_transcribe.transcribe(temp_path)
        os.unlink(temp_path)
        if result.startswith("Error:") or result.startswith("Failed"):
            raise TranscriptionError(result)
        return result
    return None


@router.message(CommandStart())
async def start(message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ask a question", callback_data="ask")]])
    await message.answer("Ready. Ask me anything or tap below.", reply_markup=kb)


@router.callback_query(lambda c: c.data == "ask")
async def on_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Type your question:")


async def run_agent(content: str, user_id: str, chat_id: int, chat_action: ChatAction):
    async def keep_typing():
        while True:
            await bot.send_chat_action(chat_id, chat_action)
            await asyncio.sleep(4)

    typing_task = asyncio.create_task(keep_typing())
    try:
        result = await client.run_agent(
            agent_id="joi",
            message=content,
            user_id=user_id,
            session_id=user_id,
        )
    finally:
        typing_task.cancel()

    parsed = result.content
    if not parsed:
        return "No response from agent", build_actions_keyboard([])
    response_text: str = parsed["content"]
    keyboard = build_actions_keyboard(parsed["suggested_actions"])
    return response_text, keyboard


@router.callback_query(ActionCallback.filter())
async def on_action(callback: CallbackQuery, callback_data: ActionCallback) -> None:
    action_text = action_cache.get(callback_data.action_id)
    if not action_text:
        await callback.answer("Action expired")
        return
    if not callback.message or not callback.from_user:
        return

    await callback.answer()
    await callback.message.answer(f"➡️ {action_text}")

    user_id = str(callback.from_user.id)
    response_text, keyboard = await run_agent(action_text, user_id, callback.message.chat.id, ChatAction.TYPING)
    converted = telegramify_markdown.markdownify(response_text)
    await callback.message.answer(converted, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)


@router.message()
async def handle(message: Message) -> None:
    if not message.from_user:
        return
    is_voice_input = message.voice is not None

    try:
        content = await get_message_content(message)
    except TranscriptionError as e:
        logger.error(f"Transcription failed: {e}")
        await message.answer("Failed to transcribe voice message.")
        return
    if not content:
        return

    user_id = str(message.from_user.id)
    chat_action = ChatAction.RECORD_VOICE if is_voice_input else ChatAction.TYPING
    response_text, keyboard = await run_agent(content, user_id, message.chat.id, chat_action)

    converted = telegramify_markdown.markdownify(response_text)
    await message.answer(converted, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)

    if is_voice_input and TTS_ENABLED:
        try:
            await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
            voice_data = await text_to_voice(response_text)
            await message.answer_voice(BufferedInputFile(voice_data, filename="voice.ogg"))
        except Exception as e:
            logger.exception(f"Voice generation error: {e}")


async def main() -> None:
    logger.info(f"Starting Joi Telegram bot... AGENTOS_URL={AGENTOS_URL}, TTS_ENABLED={TTS_ENABLED}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
