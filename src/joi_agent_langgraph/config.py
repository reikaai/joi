import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MCP_BASE_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PLAYWRIGHT_MCP_URL = os.getenv("PLAYWRIGHT_MCP_URL", "http://127.0.0.1:3100")

PERSONA_PATH = Path(__file__).parent.parent / "joi_agent" / "persona.md"
MEDIA_PERSONA_PATH = Path(__file__).parent.parent / "joi_agent" / "media_persona.md"
