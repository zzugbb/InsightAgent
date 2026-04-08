from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "sqlite.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "InsightAgent Backend"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="INSIGHT_AGENT_ENV")
    mode: str = Field(default="mock", alias="INSIGHT_AGENT_MODE")
    provider: str = Field(default="mock", alias="INSIGHT_AGENT_PROVIDER")
    model_name: str = Field(default="mock-gpt", alias="INSIGHT_AGENT_MODEL")
    base_url: str | None = Field(default=None, alias="INSIGHT_AGENT_BASE_URL")
    api_key: str | None = Field(default=None, alias="INSIGHT_AGENT_API_KEY")
    cors_origins: list[str] = Field(
        default=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        alias="INSIGHT_AGENT_CORS_ORIGINS",
    )
    sqlite_path: Path = Field(
        default=DEFAULT_SQLITE_PATH,
        alias="SQLITE_PATH",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
