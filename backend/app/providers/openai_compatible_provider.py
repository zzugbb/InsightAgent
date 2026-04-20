from __future__ import annotations

import json
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.providers.base import ProviderCallError, ProviderResponse, ProviderUsage


class OpenAICompatibleLLMProvider:
    """Provider for OpenAI-compatible `/chat/completions` APIs."""

    def __init__(
        self,
        *,
        model: str,
        provider: str,
        base_url: str,
        api_key: str,
        timeout_sec: float = 60.0,
    ) -> None:
        self.model = model
        self.provider = provider
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_sec = timeout_sec
        self._last_usage: ProviderUsage | None = None

    @property
    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _build_request(self, payload: dict[str, Any]) -> Request:
        body = json.dumps(payload).encode("utf-8")
        is_stream = bool(payload.get("stream"))
        request = Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if is_stream else "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        return request

    def _parse_error_message_from_body(self, detail: str) -> str | None:
        text = detail.strip()
        if not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text[:320]
        if not isinstance(payload, dict):
            return text[:320]
        raw_err = payload.get("error")
        if isinstance(raw_err, dict):
            msg = raw_err.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()[:320]
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()[:320]
        return text[:320]

    def _raise_http_error(self, *, exc: HTTPError, stream_mode: bool) -> None:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            detail = ""
        parsed_detail = self._parse_error_message_from_body(detail)
        is_stream = "stream" if stream_mode else "request"

        if exc.code in {401, 403}:
            raise ProviderCallError(
                code="remote_api_key_unauthorized",
                user_message=(
                    f"Remote provider {is_stream} unauthorized (HTTP {exc.code}). "
                    "Please verify API key and base URL."
                ),
                detail=parsed_detail,
                status_code=exc.code,
                retryable=False,
            ) from exc

        if exc.code == 429:
            raise ProviderCallError(
                code="remote_provider_rate_limited",
                user_message="Remote provider rate limit exceeded (HTTP 429). Please retry later.",
                detail=parsed_detail,
                status_code=exc.code,
                retryable=True,
            ) from exc

        if 500 <= exc.code <= 599:
            raise ProviderCallError(
                code="remote_provider_upstream_error",
                user_message=f"Remote provider upstream error (HTTP {exc.code}).",
                detail=parsed_detail,
                status_code=exc.code,
                retryable=True,
            ) from exc

        raise ProviderCallError(
            code="remote_provider_http_error",
            user_message=f"Remote provider {is_stream} failed with HTTP {exc.code}.",
            detail=parsed_detail,
            status_code=exc.code,
            retryable=False,
        ) from exc

    def _raise_network_error(self, *, exc: URLError, stream_mode: bool) -> None:
        kind = "stream" if stream_mode else "request"
        raise ProviderCallError(
            code="remote_provider_network_error",
            user_message=f"Remote provider {kind} network error: {exc}",
            detail=str(exc),
            retryable=True,
        ) from exc

    def _request_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._build_request(payload)
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            self._raise_http_error(exc=exc, stream_mode=False)
        except URLError as exc:
            self._raise_network_error(exc=exc, stream_mode=False)

        if not raw.strip():
            raise ProviderCallError(
                code="remote_provider_empty_response",
                user_message="Remote provider returned an empty response.",
                detail=None,
                retryable=False,
            )

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderCallError(
                code="remote_provider_invalid_json",
                user_message="Remote provider returned invalid JSON.",
                detail=raw[:256],
                retryable=False,
            ) from exc

    def _extract_message_content(self, obj: dict[str, Any]) -> str:
        choices = obj.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        return _normalize_content_text(content)

    def _extract_delta_content(self, obj: dict[str, Any]) -> str:
        choices = obj.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        delta = first.get("delta")
        if not isinstance(delta, dict):
            return ""
        content = delta.get("content")
        return _normalize_content_text(content)

    def _extract_usage(self, obj: dict[str, Any]) -> ProviderUsage | None:
        raw_usage = obj.get("usage")
        if not isinstance(raw_usage, dict):
            return None

        prompt_tokens = _normalize_usage_int(
            raw_usage.get("prompt_tokens", raw_usage.get("input_tokens"))
        )
        completion_tokens = _normalize_usage_int(
            raw_usage.get("completion_tokens", raw_usage.get("output_tokens"))
        )
        total_tokens = _normalize_usage_int(raw_usage.get("total_tokens"))

        if (
            prompt_tokens is None
            and completion_tokens is None
            and total_tokens is None
        ):
            return None

        return ProviderUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def generate(self, prompt: str) -> ProviderResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        response_obj = self._request_json(payload)
        usage = self._extract_usage(response_obj)
        self._last_usage = usage
        content = self._extract_message_content(response_obj)
        if not content.strip():
            raise ProviderCallError(
                code="remote_provider_empty_response",
                user_message="Remote provider returned empty text content.",
                detail=None,
                retryable=False,
            )
        return ProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
        )

    def stream_generate(self, prompt: str) -> Iterator[str]:
        self._last_usage = None
        base_payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        payload_candidates: list[dict[str, Any]] = [
            {**base_payload, "stream_options": {"include_usage": True}},
            base_payload,
        ]

        for idx, payload in enumerate(payload_candidates):
            yielded_chunks = 0
            done_seen = False
            request = self._build_request(payload)
            try:
                with urlopen(request, timeout=self.timeout_sec) as response:
                    for raw_line in response:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            done_seen = True
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            raise ProviderCallError(
                                code="remote_provider_stream_invalid_json",
                                user_message="Remote provider stream returned invalid JSON chunk.",
                                detail=data[:256],
                                retryable=False,
                            ) from None
                        usage = self._extract_usage(event)
                        if usage is not None:
                            self._last_usage = usage
                        delta = self._extract_delta_content(event)
                        if delta:
                            yielded_chunks += 1
                            yield delta
            except HTTPError as exc:
                can_retry_without_stream_options = (
                    idx == 0
                    and exc.code == 400
                    and "stream_options" in payload
                )
                if can_retry_without_stream_options:
                    continue
                self._raise_http_error(exc=exc, stream_mode=True)
            except URLError as exc:
                self._raise_network_error(exc=exc, stream_mode=True)
            except ProviderCallError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ProviderCallError(
                    code="remote_provider_stream_interrupted",
                    user_message=f"Remote provider stream interrupted: {exc}",
                    detail=str(exc),
                    retryable=True,
                ) from exc

            if yielded_chunks == 0:
                if done_seen:
                    raise ProviderCallError(
                        code="remote_provider_empty_response",
                        user_message="Remote provider stream finished without text output.",
                        detail=None,
                        retryable=False,
                    )
                raise ProviderCallError(
                    code="remote_provider_stream_interrupted",
                    user_message="Remote provider stream ended before completion.",
                    detail="done marker not received",
                    retryable=True,
                )
            return

    def get_last_usage(self) -> ProviderUsage | None:
        return self._last_usage


def _normalize_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def _normalize_usage_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value < 0:
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = float(text)
        except ValueError:
            return None
        if parsed < 0:
            return None
        return int(parsed)
    return None
