from __future__ import annotations

from typing import Any


def build_operations_health(settings: Any) -> dict[str, object]:
    warnings = _build_operations_warnings(settings)
    return {
        "readiness": "attention" if warnings else "ok",
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


def _build_operations_warnings(settings: Any) -> list[dict[str, str]]:
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
