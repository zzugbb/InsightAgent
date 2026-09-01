from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse


_MIN_RECOMMENDED_TASK_TIMEOUT_SEC = 30.0
_RESTORE_DRILL_MAX_AGE_DAYS = 90
_WARNING_SEVERITIES = ("critical", "warning", "info")


def build_operations_health(settings: Any) -> dict[str, object]:
    deployment = _build_deployment_health(settings)
    slo = _build_slo_health(settings)
    backup_restore = _build_backup_restore_health(settings)
    runbook = _build_runbook_health(settings)
    warnings = _build_operations_warnings(
        settings,
        deployment,
        slo,
        backup_restore,
        runbook,
    )
    warning_summary = _build_warning_summary(warnings)
    return {
        "readiness": "attention" if warnings else "ok",
        "readiness_level": warning_summary["highest_severity"] or "ok",
        "backup_restore": backup_restore,
        "deployment": deployment,
        "runbook": runbook,
        "slo": slo,
        "task_timeout_sec": float(settings.task_timeout_sec),
        "task_queue": {
            "max_concurrent": int(settings.task_queue_max_concurrent),
            "per_user_limit_enabled": int(
                settings.task_queue_max_concurrent_per_user
            )
            > 0,
            "per_session_limit_enabled": int(
                settings.task_queue_max_concurrent_per_session
            )
            > 0,
            "poll_interval_sec": float(settings.task_queue_poll_interval_sec),
        },
        "task_execution": {
            "owner_id_configured": _has_non_default_execution_owner(settings),
            "stale_recovery_enabled": float(settings.task_execution_stale_after_sec)
            > 0.0,
            "stale_after_sec": float(settings.task_execution_stale_after_sec),
            "heartbeat_interval_sec": float(
                settings.task_execution_heartbeat_interval_sec
            ),
        },
        "chroma_probe_enabled": bool(settings.chroma_probe),
        "warning_summary": warning_summary,
        "warnings": warnings,
    }


def _build_warning_summary(warnings: list[dict[str, str]]) -> dict[str, object]:
    counts = {severity: 0 for severity in _WARNING_SEVERITIES}
    for warning in warnings:
        severity = warning.get("severity", "")
        if severity in counts:
            counts[severity] += 1
    highest_severity = next(
        (severity for severity in _WARNING_SEVERITIES if counts[severity] > 0),
        None,
    )

    return {
        "total": len(warnings),
        "critical": counts["critical"],
        "warning": counts["warning"],
        "info": counts["info"],
        "highest_severity": highest_severity,
    }


def _build_runbook_health(settings: Any) -> dict[str, object]:
    return {
        "operations_runbook_configured": _has_text(
            getattr(settings, "operations_runbook_url", None)
        ),
        "incident_contact_configured": _has_text(
            getattr(settings, "incident_contact", None)
        ),
        "status_page_configured": _has_text(getattr(settings, "status_page_url", None)),
    }


def _build_backup_restore_health(settings: Any) -> dict[str, object]:
    backup_enabled = _read_bool(settings, "backup_enabled", False)
    provider_configured = bool(
        str(getattr(settings, "backup_provider", "") or "").strip()
    )
    restore_runbook_configured = bool(
        str(getattr(settings, "backup_restore_runbook_url", "") or "").strip()
    )
    drill_at = _parse_datetime(getattr(settings, "backup_last_restore_drill_at", None))
    age_days = _age_days(drill_at)
    restore_drill_recent = (
        age_days is not None and age_days <= _RESTORE_DRILL_MAX_AGE_DAYS
    )

    return {
        "backup_enabled": backup_enabled,
        "provider_configured": provider_configured,
        "restore_runbook_configured": restore_runbook_configured,
        "last_restore_drill_recorded": drill_at is not None,
        "last_restore_drill_age_days": age_days,
        "restore_drill_max_age_days": _RESTORE_DRILL_MAX_AGE_DAYS,
        "restore_drill_recent": restore_drill_recent,
    }


def _build_deployment_health(settings: Any) -> dict[str, object]:
    database_url = str(getattr(settings, "database_url", "") or "").strip()
    cors_origins = _coerce_cors_origins(getattr(settings, "cors_origins", []))
    return {
        "database_configured": bool(database_url),
        "database_kind": _classify_database_kind(database_url),
        "cors_origin_count": len(cors_origins),
        "cors_allows_localhost": _cors_allows_localhost(cors_origins),
        "cors_allows_wildcard": _cors_allows_wildcard(cors_origins),
        "remote_provider_configured": _remote_provider_configured(settings),
    }


def _build_slo_health(settings: Any) -> dict[str, object]:
    task_timeout_sec = _read_float(settings, "task_timeout_sec", 180.0)
    trace_persist_min_interval_sec = _read_float(
        settings,
        "trace_persist_min_interval_sec",
        0.35,
    )
    stream_reconnect_poll_fast_sec = _read_float(
        settings,
        "stream_reconnect_poll_fast_sec",
        0.3,
    )
    stream_reconnect_poll_max_sec = _read_float(
        settings,
        "stream_reconnect_poll_max_sec",
        2.0,
    )
    stream_reconnect_heartbeat_interval_sec = _read_float(
        settings,
        "stream_reconnect_heartbeat_interval_sec",
        2.0,
    )
    task_execution_heartbeat_interval_sec = _read_float(
        settings,
        "task_execution_heartbeat_interval_sec",
        2.0,
    )
    task_execution_stale_after_sec = _read_float(
        settings,
        "task_execution_stale_after_sec",
        0.0,
    )
    stale_recovery_margin_sec = (
        task_execution_stale_after_sec - task_execution_heartbeat_interval_sec
        if task_execution_stale_after_sec > 0
        else None
    )

    return {
        "task_timeout_sec": task_timeout_sec,
        "minimum_recommended_task_timeout_sec": _MIN_RECOMMENDED_TASK_TIMEOUT_SEC,
        "task_timeout_meets_recommended_minimum": (
            task_timeout_sec >= _MIN_RECOMMENDED_TASK_TIMEOUT_SEC
        ),
        "trace_persist_min_interval_sec": trace_persist_min_interval_sec,
        "stream_reconnect": {
            "poll_fast_sec": stream_reconnect_poll_fast_sec,
            "poll_max_sec": stream_reconnect_poll_max_sec,
            "heartbeat_interval_sec": stream_reconnect_heartbeat_interval_sec,
            "poll_backoff_order_ok": (
                stream_reconnect_poll_fast_sec <= stream_reconnect_poll_max_sec
            ),
            "heartbeat_within_task_timeout": (
                stream_reconnect_heartbeat_interval_sec < task_timeout_sec
            ),
        },
        "task_execution": {
            "heartbeat_interval_sec": task_execution_heartbeat_interval_sec,
            "stale_after_sec": task_execution_stale_after_sec,
            "stale_recovery_margin_sec": stale_recovery_margin_sec,
            "stale_recovery_margin_ok": (
                stale_recovery_margin_sec is None or stale_recovery_margin_sec > 0
            ),
        },
    }


def _build_operations_warnings(
    settings: Any,
    deployment: dict[str, object],
    slo: dict[str, object],
    backup_restore: dict[str, object],
    runbook: dict[str, object],
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    is_production = str(settings.app_env).strip().lower() == "production"
    stream_reconnect = _read_mapping(slo.get("stream_reconnect"))
    task_execution = _read_mapping(slo.get("task_execution"))

    if not _has_non_default_execution_owner(settings):
        warnings.append(
            {
                "code": "default_execution_owner",
                "severity": "warning",
                "message": "TASK_EXECUTION_OWNER_ID should be unique per backend instance.",
            }
        )
    if float(settings.task_execution_stale_after_sec) <= 0.0:
        warnings.append(
            {
                "code": "stale_recovery_disabled",
                "severity": "info",
                "message": "TASK_EXECUTION_STALE_AFTER_SEC is disabled.",
            }
        )
    if is_production and str(settings.auth_jwt_secret) == "dev-only-change-me":
        warnings.append(
            {
                "code": "default_jwt_secret",
                "severity": "critical",
                "message": "INSIGHT_AGENT_JWT_SECRET must be replaced in production.",
            }
        )
    if is_production and not str(settings.auth_secret_key or "").strip():
        warnings.append(
            {
                "code": "missing_secret_key",
                "severity": "warning",
                "message": "INSIGHT_AGENT_SECRET_KEY should be set separately in production.",
            }
        )
    if is_production and not bool(deployment["database_configured"]):
        warnings.append(
            {
                "code": "production_database_missing",
                "severity": "critical",
                "message": "INSIGHT_AGENT_DATABASE_URL must be set in production.",
            }
        )
    if is_production and _database_url_points_to_localhost(
        str(getattr(settings, "database_url", "") or "")
    ):
        warnings.append(
            {
                "code": "production_database_localhost",
                "severity": "warning",
                "message": "INSIGHT_AGENT_DATABASE_URL should not point to localhost in production.",
            }
        )
    if is_production and bool(deployment["cors_allows_wildcard"]):
        warnings.append(
            {
                "code": "production_cors_allows_wildcard",
                "severity": "critical",
                "message": "INSIGHT_AGENT_CORS_ORIGINS should not allow wildcard origins in production.",
            }
        )
    if is_production and bool(deployment["cors_allows_localhost"]):
        warnings.append(
            {
                "code": "production_cors_allows_localhost",
                "severity": "warning",
                "message": "INSIGHT_AGENT_CORS_ORIGINS should use production origins.",
            }
        )
    if not bool(deployment["remote_provider_configured"]):
        warnings.append(
            {
                "code": "remote_provider_missing_api_key",
                "severity": "critical",
                "message": "INSIGHT_AGENT_API_KEY must be set when remote provider mode is enabled.",
            }
        )
    if is_production and not bool(slo["task_timeout_meets_recommended_minimum"]):
        warnings.append(
            {
                "code": "task_timeout_below_recommended",
                "severity": "warning",
                "message": "TASK_TIMEOUT_SEC is below the recommended production minimum.",
            }
        )
    if not bool(stream_reconnect["poll_backoff_order_ok"]):
        warnings.append(
            {
                "code": "stream_reconnect_poll_backoff_inverted",
                "severity": "warning",
                "message": "STREAM_RECONNECT_POLL_FAST_SEC should be less than or equal to STREAM_RECONNECT_POLL_MAX_SEC.",
            }
        )
    if not bool(stream_reconnect["heartbeat_within_task_timeout"]):
        warnings.append(
            {
                "code": "stream_reconnect_heartbeat_exceeds_task_timeout",
                "severity": "warning",
                "message": "STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC should be lower than TASK_TIMEOUT_SEC.",
            }
        )
    if not bool(task_execution["stale_recovery_margin_ok"]):
        warnings.append(
            {
                "code": "execution_stale_window_not_above_heartbeat",
                "severity": "warning",
                "message": "TASK_EXECUTION_STALE_AFTER_SEC should be greater than TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC.",
            }
        )
    if is_production and not bool(backup_restore["backup_enabled"]):
        warnings.append(
            {
                "code": "backup_disabled",
                "severity": "critical",
                "message": "INSIGHT_AGENT_BACKUP_ENABLED should be enabled in production.",
            }
        )
    if is_production and not bool(backup_restore["provider_configured"]):
        warnings.append(
            {
                "code": "backup_provider_missing",
                "severity": "warning",
                "message": "INSIGHT_AGENT_BACKUP_PROVIDER should be set in production.",
            }
        )
    if is_production and not bool(backup_restore["restore_runbook_configured"]):
        warnings.append(
            {
                "code": "backup_restore_runbook_missing",
                "severity": "warning",
                "message": "INSIGHT_AGENT_BACKUP_RESTORE_RUNBOOK_URL should be set in production.",
            }
        )
    if is_production and not bool(backup_restore["last_restore_drill_recorded"]):
        warnings.append(
            {
                "code": "backup_restore_drill_missing",
                "severity": "warning",
                "message": "INSIGHT_AGENT_BACKUP_LAST_RESTORE_DRILL_AT should record the latest restore drill.",
            }
        )
    elif is_production and not bool(backup_restore["restore_drill_recent"]):
        warnings.append(
            {
                "code": "backup_restore_drill_stale",
                "severity": "warning",
                "message": "The latest restore drill is older than the recommended production window.",
            }
        )
    if is_production and not bool(runbook["operations_runbook_configured"]):
        warnings.append(
            {
                "code": "operations_runbook_missing",
                "severity": "critical",
                "message": "INSIGHT_AGENT_OPERATIONS_RUNBOOK_URL should be set in production.",
            }
        )
    if is_production and not bool(runbook["incident_contact_configured"]):
        warnings.append(
            {
                "code": "incident_contact_missing",
                "severity": "critical",
                "message": "INSIGHT_AGENT_INCIDENT_CONTACT should be set in production.",
            }
        )
    if is_production and not bool(runbook["status_page_configured"]):
        warnings.append(
            {
                "code": "status_page_missing",
                "severity": "info",
                "message": "INSIGHT_AGENT_STATUS_PAGE_URL should be set when an external status page exists.",
            }
        )
    if not bool(settings.chroma_probe):
        warnings.append(
            {
                "code": "chroma_probe_disabled",
                "severity": "info",
                "message": "CHROMA_PROBE is disabled, so /health will not verify Chroma reachability.",
            }
        )

    return warnings


def _has_non_default_execution_owner(settings: Any) -> bool:
    owner_id = str(settings.task_execution_owner_id or "").strip()
    return bool(owner_id and owner_id != "default")


def _coerce_cors_origins(value: Any) -> list[str]:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(origin).strip() for origin in value if str(origin).strip()]
    return []


def _classify_database_kind(database_url: str) -> str:
    if not database_url:
        return "missing"
    scheme = urlparse(database_url).scheme.lower()
    if scheme in {"postgres", "postgresql"}:
        return "postgresql"
    if scheme.startswith("sqlite"):
        return "sqlite"
    return "other"


def _database_url_points_to_localhost(database_url: str) -> bool:
    if not database_url:
        return False
    parsed = urlparse(database_url)
    hostname = (parsed.hostname or "").strip().lower()
    if hostname in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}:
        return True
    return _classify_database_kind(database_url) == "sqlite"


def _cors_allows_localhost(cors_origins: list[str]) -> bool:
    for origin in cors_origins:
        hostname = (urlparse(origin).hostname or origin).strip().lower()
        if hostname in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}:
            return True
    return False


def _cors_allows_wildcard(cors_origins: list[str]) -> bool:
    return any(origin.strip() == "*" for origin in cors_origins)


def _remote_provider_configured(settings: Any) -> bool:
    mode = str(getattr(settings, "mode", "") or "").strip().lower()
    if mode != "remote":
        return True
    provider = str(getattr(settings, "provider", "") or "").strip().lower()
    api_key = str(getattr(settings, "api_key", "") or "").strip()
    return bool(provider and provider != "mock" and api_key)


def _has_text(value: object) -> bool:
    return bool(str(value or "").strip())


def _read_float(settings: Any, field_name: str, default: float) -> float:
    try:
        return float(getattr(settings, field_name, default))
    except (TypeError, ValueError):
        return default


def _read_bool(settings: Any, field_name: str, default: bool) -> bool:
    value = getattr(settings, field_name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)


def _read_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _age_days(value: datetime | None) -> int | None:
    if value is None:
        return None
    now = datetime.now(timezone.utc)
    age = now - value.astimezone(timezone.utc)
    return max(0, age.days)
