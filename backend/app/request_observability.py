"""Low-sensitivity HTTP request measurements for pilot operations."""

from __future__ import annotations

import json
import logging
from time import monotonic
from typing import Any
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import PlainTextResponse


logger = logging.getLogger("insightagent.http")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class RequestObservabilityMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = monotonic()
        status_code = 500

        async def send_with_request_id(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                message = {
                    **message,
                    "headers": [
                        *[
                            (key, value)
                            for key, value in message.get("headers", [])
                            if key.lower() != b"x-request-id"
                        ],
                        (b"x-request-id", request_id.encode("ascii")),
                    ],
                }
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            route_template = getattr(route, "path", None)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": str(scope.get("method", "")),
                        "route": route_template if isinstance(route_template, str) else "<unmatched>",
                        "status_code": status_code,
                        "duration_ms": round((monotonic() - started_at) * 1000, 3),
                    },
                    separators=(",", ":"),
                )
            )


def add_request_observability(app: Any) -> None:
    app.add_middleware(RequestObservabilityMiddleware)
    if Exception not in app.exception_handlers:
        app.add_exception_handler(Exception, _unhandled_error_response)


def _unhandled_error_response(request: Request, _exc: Exception) -> PlainTextResponse:
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if isinstance(request_id, str) else None
    return PlainTextResponse("Internal Server Error", status_code=500, headers=headers)
