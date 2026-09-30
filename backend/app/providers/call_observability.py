"""Low-sensitivity, one-line telemetry for remote HTTP provider attempts."""

from __future__ import annotations

import json
import logging
from time import monotonic


logger = logging.getLogger("insightagent.llm")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def record_provider_attempt(
    *, mode: str, outcome: str, started_at: float, status_code: int | None = None,
    usage_available: bool = False,
) -> None:
    status_family = f"{status_code // 100}xx" if status_code is not None else None
    logger.info(json.dumps({
        "event": "llm_http_attempt",
        "mode": mode,
        "outcome": outcome,
        "status_family": status_family,
        "duration_ms": round((monotonic() - started_at) * 1000, 3),
        "usage_available": usage_available,
    }, separators=(",", ":")))
