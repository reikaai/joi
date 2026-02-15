from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_model: str = "gpt-4o-mini"
    mcp_url: str = "http://127.0.0.1:8000"
    openrouter_api_key: str | None = None
    anthropic_api_key: str | None = None

    @computed_field
    @property
    def logs_dir(self) -> Path:
        return _ROOT / "logs"

    @computed_field
    @property
    def data_dir(self) -> Path:
        return _ROOT / "data"

    @computed_field
    @property
    def persona_path(self) -> Path:
        return Path(__file__).parent.parent / "joi_agent" / "persona.md"

    @computed_field
    @property
    def media_persona_path(self) -> Path:
        return Path(__file__).parent.parent / "joi_agent" / "media_persona.md"

    @property
    def mem0_config(self) -> dict:
        return {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "openrouter_base_url": "https://openrouter.ai/api/v1",
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": self.openrouter_api_key,
                    "openai_base_url": "https://openrouter.ai/api/v1",
                },
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "joi_memories",
                    "path": str(self.data_dir / "qdrant"),
                },
            },
        }


settings = Settings()
settings.logs_dir.mkdir(exist_ok=True)
settings.data_dir.mkdir(exist_ok=True)
