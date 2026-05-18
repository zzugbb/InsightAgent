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
    tool_registry_overrides_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_OVERRIDES_JSON",
        description="Tool registry override JSON；用于覆盖已注册 tool 的标签、超时、重试、上下文字段，或通过 enabled=false 禁用 tool",
    )
    tool_registry_profile: str = Field(
        default="default",
        alias="INSIGHT_AGENT_TOOL_REGISTRY_PROFILE",
        description="Tool registry profile；用于按环境启用内建 tool 组合，再叠加 JSON overrides",
    )
    tool_registry_extra_tools_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON",
        description="Tool registry extra tools JSON；用于基于现有 template tool 生成额外 alias registrations，再参与 profile/override 组合链",
    )
    tool_registry_provider_source: str = Field(
        default="default",
        alias="INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCE",
        description="Tool registry provider source；用于选择命名基础 registry source，再叠加 profile/disable/override/extra tool 配置",
    )
    tool_registry_loaders_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_LOADERS_JSON",
        description="Tool registry loaders JSON；用于定义可复用命名 loader，支持 loader_factory/loader/registry_file/profile/disabled/overrides/extra_tools adapter 形态，其中 registry_file 可指向 pure extra_tools 文件、manifest 文件，或带 registry_files/registry_dirs 的 composed manifest",
    )
    tool_registry_loader_factories_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_LOADER_FACTORIES_JSON",
        description="Tool registry loader factories JSON；用于定义可复用命名 loader_factory 别名，映射到内建或已声明的 loader_factory，或通过 registry_file 绑定文件型 registry source（支持 pure extra_tools / manifest / registry_files / registry_dirs 几种文件形态）",
    )
    tool_registry_providers_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_PROVIDERS_JSON",
        description="Tool registry providers JSON；用于定义可复用命名 provider，支持 provider_factory/loader/provider/registry_file/profile/disabled/overrides/extra_tools adapter 形态，其中 loader 可引用命名 loaders，registry_file 可指向 pure extra_tools 文件、manifest 文件，或带 registry_files/registry_dirs 的 composed manifest",
    )
    tool_registry_provider_factories_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_FACTORIES_JSON",
        description="Tool registry provider factories JSON；用于定义可复用命名 provider_factory 别名，映射到内建或已声明的 provider_factory，或通过 registry_file 绑定文件型 registry source（支持 pure extra_tools / manifest / registry_files / registry_dirs 几种文件形态）",
    )
    tool_registry_provider_sources_json: str | None = Field(
        default=None,
        alias="INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCES_JSON",
        description="Tool registry provider sources JSON；用于定义命名基础 registry source，支持 provider_factory/provider/loader/registry_file/profile/disabled/overrides/extra_tools adapter 形态，并可引用命名 providers 与 named loaders；registry_file 可指向 pure extra_tools 文件、manifest 文件，或带 registry_files/registry_dirs 的 composed manifest",
    )

    @property
    def chroma_http_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
