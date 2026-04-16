from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


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
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        ],
        alias="INSIGHT_AGENT_CORS_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql://insight:insight@127.0.0.1:5432/insightagent",
        alias="INSIGHT_AGENT_DATABASE_URL",
        description="PostgreSQL 连接串",
    )
    chroma_host: str = Field(
        default="127.0.0.1",
        alias="CHROMA_HOST",
        description="Chroma HTTP 服务主机；与 backend 同 Compose 网络时可填服务名 chroma",
    )
    chroma_port: int = Field(
        default=8001,
        ge=1,
        le=65535,
        alias="CHROMA_PORT",
        description="Chroma 映射端口；docker-compose 默认 8001:8000",
    )
    chroma_probe: bool = Field(
        default=True,
        alias="CHROMA_PROBE",
        description="是否在 /health 中对 Chroma 发起心跳探测（可关以避免阻塞）",
    )
    trace_persist_min_interval_sec: float = Field(
        default=0.35,
        ge=0.0,
        alias="TRACE_PERSIST_MIN_INTERVAL_SEC",
        description="trace 增量写入最小间隔（秒）；0 表示不节流",
    )
    stream_reconnect_poll_fast_sec: float = Field(
        default=0.3,
        gt=0.0,
        alias="STREAM_RECONNECT_POLL_FAST_SEC",
        description="running 重连流有增量时的快轮询间隔（秒）",
    )
    stream_reconnect_poll_max_sec: float = Field(
        default=2.0,
        gt=0.0,
        alias="STREAM_RECONNECT_POLL_MAX_SEC",
        description="running 重连流无增量退避到的最大轮询间隔（秒）",
    )
    stream_reconnect_heartbeat_interval_sec: float = Field(
        default=2.0,
        gt=0.0,
        alias="STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC",
        description="running 重连流 heartbeat 周期（秒）",
    )
    task_timeout_sec: float = Field(
        default=180.0,
        gt=0.0,
        alias="TASK_TIMEOUT_SEC",
        description="单任务流式执行超时阈值（秒）",
    )
    rag_default_knowledge_base_id: str = Field(
        default="default",
        alias="RAG_DEFAULT_KNOWLEDGE_BASE_ID",
        description="RAG 默认知识库 ID",
    )
    rag_default_top_k: int = Field(
        default=4,
        ge=1,
        le=20,
        alias="RAG_DEFAULT_TOP_K",
        description="RAG 默认检索条数",
    )
    usage_prompt_token_price_per_1k: float = Field(
        default=0.001,
        ge=0.0,
        alias="USAGE_PROMPT_TOKEN_PRICE_PER_1K",
        description="prompt tokens 每 1k 估算单价（USD）",
    )
    usage_completion_token_price_per_1k: float = Field(
        default=0.002,
        ge=0.0,
        alias="USAGE_COMPLETION_TOKEN_PRICE_PER_1K",
        description="completion tokens 每 1k 估算单价（USD）",
    )
    auth_jwt_secret: str = Field(
        default="dev-only-change-me",
        alias="INSIGHT_AGENT_JWT_SECRET",
        description="JWT HS256 签名密钥（生产环境必须替换）",
    )
    auth_access_token_ttl_minutes: int = Field(
        default=7 * 24 * 60,
        ge=5,
        le=60 * 24 * 30,
        alias="INSIGHT_AGENT_ACCESS_TOKEN_TTL_MINUTES",
        description="访问令牌有效期（分钟）",
    )
    auth_refresh_token_ttl_days: int = Field(
        default=30,
        ge=1,
        le=180,
        alias="INSIGHT_AGENT_REFRESH_TOKEN_TTL_DAYS",
        description="刷新令牌有效期（天）",
    )
    auth_secret_key: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_SECRET_KEY",
        description="用户密钥加密主密钥；为空时回退 JWT 密钥（仅开发建议）",
    )

    @property
    def chroma_http_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
