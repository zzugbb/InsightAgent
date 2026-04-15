from __future__ import annotations

import json
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.providers.base import ProviderResponse


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

    @property
    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _build_request(self, payload: dict[str, Any]) -> Request:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        return request

    def _request_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._build_request(payload)
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")
            except Exception:  # noqa: BLE001
                detail = ""
            message = f"Remote provider request failed: HTTP {exc.code}"
            if detail:
                message = f"{message}, detail={detail}"
            raise RuntimeError(message) from exc
        except URLError as exc:
            raise RuntimeError(f"Remote provider network error: {exc}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Remote provider returned invalid JSON: {raw[:256]}") from exc

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

    def generate(self, prompt: str) -> ProviderResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        response_obj = self._request_json(payload)
        content = self._extract_message_content(response_obj)
        return ProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider,
        )

    def stream_generate(self, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
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
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = self._extract_delta_content(event)
                    if delta:
                        yield delta
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")
            except Exception:  # noqa: BLE001
                detail = ""
            message = f"Remote provider stream failed: HTTP {exc.code}"
            if detail:
                message = f"{message}, detail={detail}"
            raise RuntimeError(message) from exc
        except URLError as exc:
            raise RuntimeError(f"Remote provider stream network error: {exc}") from exc


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
