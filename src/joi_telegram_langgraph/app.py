import os
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from dotenv import load_dotenv
from langgraph_sdk import get_client
from loguru import logger

load_dotenv()

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logger.add(LOGS_DIR / "joi_telegram_langgraph.log", rotation="10 MB", retention="7 days")

LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:2024")
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "joi")

langgraph = get_client(url=LANGGRAPH_URL)

bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
router = Router()
dp = Dispatcher()
dp.include_router(router)
