from __future__ import annotations

from typing import Any

from app.providers.base import ProviderUsage

_MISSING = object()
_USAGE_KEYS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "input_tokens",
    "output_tokens",
)
_RESPONSE_TEXT_KEYS = ("output_text", "text")
_RESPONSE_NESTED_KEYS = ("content", "message", "delta", "output", "choices")


def _read_field(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key, _MISSING)
    try:
        return getattr(value, key)
    except Exception:  # noqa: BLE001
        return _MISSING


def _has_field(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value
    return _read_field(value, key) is not _MISSING


def _is_response_sequence(value: object) -> bool:
    return isinstance(value, (list, tuple))


def normalize_usage_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = float(text)
        except ValueError:
            return None
        return int(parsed) if parsed >= 0 else None
    return None


def coerce_provider_usage(value: object) -> ProviderUsage | None:
    if isinstance(value, ProviderUsage):
        return value
    if value is None:
        return None
    if not any(_has_field(value, key) for key in _USAGE_KEYS):
        return None
    prompt_tokens = normalize_usage_int(
        _read_field(value, "prompt_tokens")
    )
    completion_tokens = normalize_usage_int(
        _read_field(value, "completion_tokens")
    )
    total_tokens = normalize_usage_int(_read_field(value, "total_tokens"))
    if prompt_tokens is None:
        prompt_tokens = normalize_usage_int(_read_field(value, "input_tokens"))
    if completion_tokens is None:
        completion_tokens = normalize_usage_int(_read_field(value, "output_tokens"))
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


def normalize_response_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) or any(
        _has_field(value, key)
        for key in _RESPONSE_TEXT_KEYS + _RESPONSE_NESTED_KEYS
    ):
        output_text = _read_field(value, "output_text")
        if isinstance(output_text, str):
            return output_text
        text_value = _read_field(value, "text")
        if isinstance(text_value, str):
            return text_value
        for key in _RESPONSE_NESTED_KEYS:
            nested_value = _read_field(value, key)
            if nested_value is None or nested_value is _MISSING:
                continue
            nested_text = normalize_response_text(nested_value)
            if nested_text:
                return nested_text
        return ""
    if not _is_response_sequence(value):
        return ""
    parts: list[str] = []
    for item in value:
        normalized = normalize_response_text(item)
        if normalized:
            parts.append(normalized)
    return "".join(parts)


def extract_response_text(response: object) -> str:
    normalized = normalize_response_text(response)
    if normalized:
        return normalized
    for key in ("content", "output_text", "text", "output", "choices"):
        nested_value = _read_field(response, key)
        if nested_value is _MISSING:
            continue
        nested = normalize_response_text(nested_value)
        if nested:
            return nested
    return ""


def extract_response_delta_text(response: object) -> str:
    choices = _read_field(response, "choices")
    if _is_response_sequence(choices) and choices:
        delta = _read_field(choices[0], "delta")
        if delta is not _MISSING:
            nested = normalize_response_text(delta)
            if nested:
                return nested
    for key in ("delta", "output_text", "text", "content"):
        nested_value = _read_field(response, key)
        if nested_value is _MISSING:
            continue
        nested = normalize_response_text(nested_value)
        if nested:
            return nested
    if choices is _MISSING:
        return ""
    nested = extract_response_delta_text({"choices": choices})
    if nested:
        return nested
    return ""
