from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services.audit_service import (
    SUPPORTED_AUDIT_EVENT_TYPES,
    count_audit_logs,
    list_audit_logs,
    normalize_audit_event_type,
)


router = APIRouter()


class AuditLogItemResponse(BaseModel):
    id: str
    event_type: str
    event_detail: dict[str, Any] | None = None
    session_id: str | None = None
    task_id: str | None = None
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int = Field(description="符合条件的审计事件总数")
    limit: int
    offset: int
    has_more: bool


def _validate_iso8601(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must be ISO8601 datetime",
        ) from exc
    return text


def _parse_event_detail(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


@router.get("/logs", response_model=AuditLogListResponse)
def get_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=50_000),
    event_type: str | None = Query(
        default=None,
        description=(
            "可选：按事件类型过滤（login/logout/refresh/settings_update/"
            "settings_validate/task_create/task_cancel/task_timeout/task_failed/"
            "rag_ingest/rag_kb_clear/rag_kb_delete）"
        ),
    ),
    session_id: str | None = Query(default=None, description="可选：按会话 ID 过滤"),
    task_id: str | None = Query(default=None, description="可选：按任务 ID 过滤"),
    start_at: str | None = Query(default=None, description="可选：开始时间（ISO8601）"),
    end_at: str | None = Query(default=None, description="可选：结束时间（ISO8601）"),
    current_user: dict = Depends(get_current_user),
) -> AuditLogListResponse:
    normalized_event_type: str | None = None
    if isinstance(event_type, str):
        raw = event_type.strip()
        if raw:
            try:
                normalized_event_type = normalize_audit_event_type(raw)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if normalized_event_type not in SUPPORTED_AUDIT_EVENT_TYPES:
                raise HTTPException(status_code=422, detail="unsupported event_type")

    start_iso = _validate_iso8601("start_at", start_at)
    end_iso = _validate_iso8601("end_at", end_at)
    if start_iso and end_iso and start_iso > end_iso:
        raise HTTPException(status_code=422, detail="start_at must be <= end_at")

    user_id = str(current_user["id"])
    rows = list_audit_logs(
        user_id=user_id,
        limit=limit,
        offset=offset,
        event_type=normalized_event_type,
        session_id=session_id,
        task_id=task_id,
        start_at=start_iso,
        end_at=end_iso,
    )
    total = count_audit_logs(
        user_id=user_id,
        event_type=normalized_event_type,
        session_id=session_id,
        task_id=task_id,
        start_at=start_iso,
        end_at=end_iso,
    )
    items: list[AuditLogItemResponse] = []
    for row in rows:
        detail = _parse_event_detail(row.get("event_detail_json"))
        resolved_session_id = (
            str(detail.get("session_id")).strip()
            if isinstance(detail, dict) and isinstance(detail.get("session_id"), str)
            else None
        )
        resolved_task_id = (
            str(detail.get("task_id")).strip()
            if isinstance(detail, dict) and isinstance(detail.get("task_id"), str)
            else None
        )
        items.append(
            AuditLogItemResponse(
                id=str(row["id"]),
                event_type=str(row["event_type"]),
                event_detail=detail,
                session_id=resolved_session_id or None,
                task_id=resolved_task_id or None,
                created_at=str(row["created_at"]),
            )
        )
    return AuditLogListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(rows) < total,
    )
