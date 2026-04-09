"""
与主计划 TraceStep 契约及前端 `lib/types/trace.ts` 对齐的最小 OpenAPI 模型。
持久化层仍为 JSON；此处用于响应校验与文档显式化。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceStepMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = None
    step_type: str | None = None
    tokens: int | None = None
    cost_estimate: float | None = None
    latency: float | None = None
    retryCount: int | None = None
    prompt: str | None = None
    label: str | None = None
    tool: dict[str, Any] | None = None
    rag: dict[str, Any] | None = None
    memory: list[str] | None = None


class TraceStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str = Field(
        ...,
        description="三大类：thought / action / observation；扩展类型仍用 string",
    )
    content: str
    seq: int | None = Field(
        default=None,
        description="与 trace delta 游标对齐；缺省时由持久化层按序填充",
    )
    meta: TraceStepMeta | None = None


def parse_trace_steps(steps: list[dict]) -> list[TraceStep]:
    """将 SQLite 中 JSON 反序列化后的 dict 转为显式模型（供 OpenAPI 与校验）。"""
    return [TraceStep.model_validate(s) for s in steps]
