from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def build_operations_health(settings: Any) -> dict[str, object]:
    deployment = _build_deployment_health(settings)
    warnings = _build_operations_warnings(settings, deployment)
    return {
        "readiness": "attention" if warnings else "ok",
        "deployment": deployment,
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
        "warnings": warnings,
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


def _build_operations_warnings(
    settings: Any,
    deployment: dict[str, object],
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    is_production = str(settings.app_env).strip().lower() == "production"

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
