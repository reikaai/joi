from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from langgraph_sdk import get_client
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    langgraph_url: str = "http://localhost:2024"
    assistant_id: str = "joi"
    joi_debug_stats: bool = False


settings = Settings()

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logger.add(LOGS_DIR / "joi_telegram_langgraph.log", rotation="10 MB", retention="7 days")

langgraph = get_client(url=settings.langgraph_url)
bot = Bot(token=settings.telegram_bot_token)
router = Router()
dp = Dispatcher()
dp.include_router(router)
